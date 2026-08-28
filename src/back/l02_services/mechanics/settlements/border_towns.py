"""
Сервис пограничных городов: основание поселения на свободном гексе,
подъем его уровня и выкуп смежных земель.

Разделение ответственности здесь такое же, как у гарнизонов: все, что
касается самого города (потолок уровня, смежность и лимит земель), проверяет
агрегат BorderTown, а сервис отвечает за карту и казну - свободен ли гекс,
хватает ли ресурсов и что после этого меняется в мире.

Порядок операций в каждом приказе один и тот же: сначала все проверки,
потом списание казны и только затем изменение мира. Иначе отказ на середине
оставил бы фракцию без денег и без города.
"""

from typing import Optional

from src.back.l01_domain.exceptions.factions import (
    BorderTownNotFoundError,
    FactionNotFoundError,
    InvalidSettlementPlacementError,
)
from src.back.l01_domain.factions.constants import (
    BORDER_TOWN_FOUNDATION_COST,
    BORDER_TOWN_LAND_CLAIM_COST,
    border_town_upgrade_cost,
)
from src.back.l01_domain.factions.models.border_town import BorderTown
from src.back.l01_domain.factions.models.buildings import RegionalHall
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.models.strategic import HexCoordinates, hex_zone_id
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.event.registry import GameEvents


class BorderTownService:
    """
    Исполняет приказы игрока по пограничным городам.
    """

    def __init__(self, event_bus: Optional[EventBusProtocol] = None) -> None:
        self._event_bus = event_bus

    # ==================================================================
    # ОСНОВАНИЕ ГОРОДА
    # ==================================================================

    async def found_border_town(
        self,
        world_state: WorldState,
        faction_id: str,
        target_hex: HexCoordinates,
        name: str,
    ) -> BorderTown:
        """
        Ставит новое поселение на свободный гекс карты.

        Город встает сразу на первом уровне с двумя строительными слотами и
        без единой союзной земли: их предстоит выкупать отдельно.
        """
        faction = self._require_faction(world_state, faction_id)
        self._assert_hex_is_free(world_state, faction_id, target_hex)

        faction.spend_all(BORDER_TOWN_FOUNDATION_COST)

        town = BorderTown(
            faction_id=faction.id,
            name=name,
            center_hex=target_hex,
        )
        town.register_investment(BORDER_TOWN_FOUNDATION_COST)

        faction.add_border_town(town)
        faction.gain_zone(town.zone_id)
        self._occupy_hex(world_state, target_hex)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.BORDER_TOWN_FOUNDED,
                faction_id=faction.id,
                town_id=town.id,
                town_name=town.name,
                zone_id=town.zone_id,
                hex=target_hex.model_dump(),
            )

        return town

    # ==================================================================
    # РОСТ ГОРОДА
    # ==================================================================

    async def upgrade_border_town(
        self,
        world_state: WorldState,
        faction_id: str,
        town_id: str,
    ) -> BorderTown:
        """
        Поднимает город на уровень выше: +1 строительный слот внутри стен
        и больше ополчения в его гарнизоне со следующего такта.
        """
        faction = self._require_faction(world_state, faction_id)
        town = self._require_town(faction, town_id)

        town.assert_can_upgrade()
        cost = border_town_upgrade_cost(town.level + 1)

        faction.spend_all(cost)
        town.upgrade()
        town.register_investment(cost)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.BORDER_TOWN_UPGRADED,
                faction_id=faction.id,
                town_id=town.id,
                town_name=town.name,
                level=town.level,
                building_slots=town.building_slots,
            )

        return town

    # ==================================================================
    # ЗАСЕЛЕНИЕ СМЕЖНЫХ ЗЕМЕЛЬ
    # ==================================================================

    async def claim_border_land(
        self,
        world_state: WorldState,
        faction_id: str,
        town_id: str,
        target_hex: HexCoordinates,
    ) -> BorderTown:
        """
        Выкупает смежный с городом гекс в союзные земли фракции.

        На купленной земле сразу встает ратуша: с этого такта земля дает
        строительный слот, платит подушный сбор и поднимает свое ополчение.
        """
        faction = self._require_faction(world_state, faction_id)
        town = self._require_town(faction, town_id)

        self._assert_hex_is_free(world_state, faction_id, target_hex)
        town.assert_can_claim_land(target_hex)

        faction.spend_all(BORDER_TOWN_LAND_CLAIM_COST)

        town.claim_land(target_hex)
        town.register_investment(BORDER_TOWN_LAND_CLAIM_COST)

        zone_id = hex_zone_id(target_hex)
        faction.gain_zone(zone_id)
        faction.add_regional_hall(
            RegionalHall(
                faction_id=faction.id,
                zone_id=zone_id,
                name=f"Ратуша поселения {town.name}",
            )
        )
        self._occupy_hex(world_state, target_hex)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.BORDER_TOWN_LAND_CLAIMED,
                faction_id=faction.id,
                town_id=town.id,
                town_name=town.name,
                zone_id=zone_id,
                hex=target_hex.model_dump(),
                free_land_slots=town.free_land_slots,
            )

        return town

    # ==================================================================
    # ЧТЕНИЕ
    # ==================================================================

    def list_border_towns(
        self, world_state: WorldState, faction_id: str
    ) -> list[BorderTown]:
        """Все пограничные города фракции для окна управления державой."""
        return list(self._require_faction(world_state, faction_id).border_towns)

    # ==================================================================
    # ВСПОМОГАТЕЛЬНОЕ
    # ==================================================================

    @staticmethod
    def _require_faction(world_state: WorldState, faction_id: str) -> Faction:
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise FactionNotFoundError(faction_id)
        return faction

    @staticmethod
    def _require_town(faction: Faction, town_id: str) -> BorderTown:
        town = faction.get_border_town(town_id)
        if town is None:
            raise BorderTownNotFoundError(town_id=town_id, faction_id=faction.id)
        return town

    @staticmethod
    def _assert_hex_is_free(
        world_state: WorldState, faction_id: str, coord: HexCoordinates
    ) -> None:
        """
        Убеждается, что гекс действительно ничей.

        Занятым считается все, что уже кому-то принадлежит или на чем стоит
        чужая сила: столица и союзные земли любой фракции (включая свои
        собственные - второй город на той же земле не поставить), ориентир
        Ничьей земли и вражеское войско на самом гексе.
        """
        zone_id = hex_zone_id(coord)

        for faction in world_state.factions.values():
            if faction.capital_hex == coord:
                raise InvalidSettlementPlacementError(
                    zone_id, f"здесь стоит цитадель фракции '{faction.id}'"
                )
            if zone_id in faction.controlled_zone_ids:
                raise InvalidSettlementPlacementError(
                    zone_id, f"земля уже принадлежит фракции '{faction.id}'"
                )

        if world_state.get_point_of_interest_at(coord) is not None:
            raise InvalidSettlementPlacementError(
                zone_id, "гекс занят ориентиром Ничьей земли"
            )

        foreign_army = next(
            (
                army
                for army in world_state.get_armies_at_hex(coord)
                if army.faction_id != faction_id
            ),
            None,
        )
        if foreign_army is not None:
            raise InvalidSettlementPlacementError(
                zone_id, f"на гексе стоит чужое войско '{foreign_army.name}'"
            )

    @staticmethod
    def _occupy_hex(world_state: WorldState, coord: HexCoordinates) -> None:
        """
        Вычеркивает гекс из Ничьей земли: он больше не нейтральный, и
        экспедиции рабочих туда уже не отправить.
        """
        if coord in world_state.neutral_hexes:
            world_state.neutral_hexes.remove(coord)
