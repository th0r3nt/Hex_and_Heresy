"""
Фасад.
Точка входа для остальных модулей.

Калькулятор умеет только считать геометрию обзора, фильтр - только резать
срез мира. Фасад решает, что с этим делать: раскладывает пересчитанный обзор
по маскам фракций, копит историю открытых гексов и трубит о чужих армиях,
которые разведка вскрыла именно на этом такте.

Своего состояния фасад не держит - весь туман живет в самом WorldState,
поэтому один и тот же экземпляр годится и для шага глобального такта, и
для внеочередного запроса среза карты из интерфейса.
"""

from dataclasses import dataclass
from typing import Optional

from src.back.l01_domain.maps.constants import HexVisibilityState
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.reports import VisionStepReport
from src.back.l01_domain.world.models.state import WorldState
from src.back.l01_domain.world.models.visibility import FactionVisionMap
from src.back.l02_services.mechanics.vision.calculator import VisionCalculator
from src.back.l02_services.mechanics.vision.filter import VisionFilter
from src.back.utils.event.registry import GameEvents


@dataclass(frozen=True)
class _FactionVisionOutcome:
    """
    Итог пересчета обзора одной фракции - внутренняя сводка для отчета такта.
    """

    newly_explored_count: int
    army_ids: list[str]


class VisionFacade:
    """
    Оркестрирует пересчет тумана войны и выдачу отфильтрованных срезов мира.
    """

    def __init__(
        self,
        calculator: Optional[VisionCalculator] = None,
        vision_filter: Optional[VisionFilter] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._calculator = calculator or VisionCalculator()
        self._filter = vision_filter or VisionFilter()
        self._event_bus = event_bus

    # ==================================================================
    # ПЕРЕСЧЕТ ТУМАНА НА ТАКТЕ
    # ==================================================================

    async def refresh_world_vision(self, world_state: WorldState) -> VisionStepReport:
        """
        Пересчитывает обзор всех фракций партии и обновляет их маски тумана.

        Считается после марша: обзор должен отвечать позициям армий на конец
        такта, иначе разведка отставала бы от собственной колонны на ход.
        """
        report = VisionStepReport()

        for faction_id in list(world_state.factions.keys()):
            spotted = await self._refresh_faction_vision(world_state, faction_id)
            vision_map = world_state.get_or_create_vision_map(faction_id)

            report.visible_hexes_by_faction[faction_id] = len(vision_map.visible_hexes)
            report.newly_explored_by_faction[faction_id] = spotted.newly_explored_count
            if spotted.army_ids:
                report.spotted_army_ids_by_faction[faction_id] = spotted.army_ids

        return report

    async def _refresh_faction_vision(
        self, world_state: WorldState, faction_id: str
    ) -> _FactionVisionOutcome:
        """
        Пересчитывает обзор одной фракции и объявляет о том, что он вскрыл.

        Чужие армии сравниваются с прошлым тактом: событие поднимается только
        на те, что вошли в поле зрения именно сейчас, - иначе о стоящем рядом
        враге трубили бы каждый такт подряд.
        """
        vision_map = world_state.get_or_create_vision_map(faction_id)

        vision_map.clear_direct_vision()
        visible = self._calculator.calculate_visible_hexes(world_state, faction_id)
        newly_explored = vision_map.reveal(visible)

        spotted_army_ids = sorted(
            vision_map.track_spotted_armies(
                self._collect_visible_foreign_armies(world_state, faction_id, visible)
            )
        )

        await self._publish_vision_updated(faction_id, vision_map, newly_explored)
        for army_id in spotted_army_ids:
            await self._publish_army_spotted(world_state, faction_id, army_id)

        return _FactionVisionOutcome(
            newly_explored_count=len(newly_explored),
            army_ids=spotted_army_ids,
        )

    @staticmethod
    def _collect_visible_foreign_armies(
        world_state: WorldState,
        faction_id: str,
        visible: set[HexCoordinates],
    ) -> set[str]:
        """
        Чужие армии, которые фракция видит на этом такте.

        Что из них новость, а что нет, решает уже сама маска: она помнит,
        кого видела на прошлом такте.
        """
        return {
            army.id
            for army in world_state.armies.values()
            if army.faction_id != faction_id and army.current_hex in visible
        }

    # ==================================================================
    # ЧТЕНИЕ ОБЗОРА
    # ==================================================================

    def get_vision_map(
        self, world_state: WorldState, faction_id: str
    ) -> FactionVisionMap:
        """
        Текущая маска тумана фракции для слоя карты в интерфейсе.
        """
        return world_state.get_or_create_vision_map(faction_id)

    def get_hex_status(
        self, world_state: WorldState, faction_id: str, coord: HexCoordinates
    ) -> HexVisibilityState:
        """
        Состояние одного гекса глазами фракции.
        """
        return world_state.get_hex_visibility(faction_id, coord)

    def is_hex_visible(
        self, world_state: WorldState, faction_id: str, coord: HexCoordinates
    ) -> bool:
        """
        Просматривает ли фракция гекс прямо сейчас - гейт для ленты событий.
        """
        return world_state.is_hex_visible_to(faction_id, coord)

    def build_world_view(
        self, world_state: WorldState, faction_id: str
    ) -> WorldState:
        """
        Срез мира глазами фракции: без чужих армий, гонцов и неоткрытых земель.
        """
        return self._filter.filter_world_for_faction(world_state, faction_id)

    # ==================================================================
    # ОБЪЯВЛЕНИЯ НА ШИНЕ
    # ==================================================================

    async def _publish_vision_updated(
        self,
        faction_id: str,
        vision_map: FactionVisionMap,
        newly_explored: set[HexCoordinates],
    ) -> None:
        """
        Сообщает о пересчете тумана: интерфейсу пора перерисовать слой карты.

        Молчим, когда открывать нечего: перерисовывать неизменившийся туман
        каждый такт незачем.
        """
        if self._event_bus is None or not newly_explored:
            return

        await self._event_bus.publish(
            GameEvents.Strategic.VISION_UPDATED,
            observer_faction_id=faction_id,
            visible_hexes_count=len(vision_map.visible_hexes),
            explored_hexes_count=len(vision_map.explored_hexes),
            newly_explored_hexes=sorted(
                newly_explored, key=lambda coord: (coord.q, coord.r)
            ),
        )

    async def _publish_army_spotted(
        self, world_state: WorldState, faction_id: str, army_id: str
    ) -> None:
        """
        Сообщает о вскрытой разведкой чужой армии.

        Событие адресное: в нем указано, чьи именно глаза увидели врага,
        поэтому мост в сокет отдает его только этому наблюдателю.
        """
        if self._event_bus is None:
            return

        army = world_state.get_army(army_id)
        if army is None:
            return

        await self._event_bus.publish(
            GameEvents.Strategic.ARMY_SPOTTED,
            observer_faction_id=faction_id,
            army_id=army.id,
            owner_faction_id=army.faction_id,
            army_name=army.name,
            hex_coords=army.current_hex,
        )

