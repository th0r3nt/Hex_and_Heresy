"""
Судьба побежденного пограничного города: что победитель решил с ним
сделать и как это доводится до конца.

Разрушение, разграбление и захват - не мгновенное действие, а операция на
2-3 такта (BorderTownOperation). Здесь живут обе ее половины: проверка
права начать и обратный отсчет на глобальном такте. Сами последствия
применяет BorderTownOutcomes.
"""

from random import Random
from typing import Optional

from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.exceptions.factions import (
    BorderTownOperationInProgressError,
    BorderTownResolutionInvalidError,
)
from src.back.l01_domain.factions.constants import BorderTownResolutionType
from src.back.l01_domain.factions.models.border_town import (
    BorderTown,
    BorderTownOperation,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.reports import BorderTownResolutionStepReport
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.settlements.border_towns.common import (
    require_army,
    require_town_on_map,
)
from src.back.l02_services.mechanics.settlements.border_towns.outcomes import (
    BorderTownOutcomes,
)
from src.back.utils.event.registry import GameEvents


class BorderTownResolutionService:
    """
    Ведет операции над взятыми штурмом городами от приказа до последствий.
    """

    def __init__(
        self,
        event_bus: Optional[EventBusProtocol] = None,
        rng: Optional[Random] = None,
        outcomes: Optional[BorderTownOutcomes] = None,
    ) -> None:
        self._event_bus = event_bus
        self._outcomes = outcomes or BorderTownOutcomes(event_bus=event_bus, rng=rng)

    # ==================================================================
    # НАЧАЛО ОПЕРАЦИИ
    # ==================================================================

    async def initiate_town_resolution(
        self,
        world_state: WorldState,
        town_id: str,
        army_id: str,
        resolution_type: BorderTownResolutionType,
    ) -> Optional[BorderTownOperation]:
        """
        Начинает то, что победитель решил сделать с побежденным городом.

        Возвращает заведенную операцию либо None, если победитель выбрал
        пройти мимо: пропуск ничего не меняет и ждать его нечего.
        """
        owner, town = require_town_on_map(world_state, town_id)
        army = require_army(world_state, army_id)

        self._assert_town_is_defeated(world_state, owner, town, army)

        if resolution_type is BorderTownResolutionType.IGNORE:
            await self._publish_resolution_started(town, army, resolution_type, None)
            return None

        operation = BorderTownOperation.start(
            town=town,
            army_id=army.id,
            conqueror_faction_id=army.faction_id,
            resolution_type=resolution_type,
        )

        # Армия встает лагерем на гексе, а город и его гарнизон замирают:
        # пока идет операция, ополчение не набирается и не лечится
        army.lock_in_operation(operation.id)
        self._set_town_garrison_lock(world_state, town, locked=True)
        world_state.add_border_town_operation(operation)

        await self._publish_resolution_started(town, army, resolution_type, operation)

        return operation

    @staticmethod
    def _assert_town_is_defeated(
        world_state: WorldState,
        owner: Faction,
        town: BorderTown,
        army: StrategicArmy,
    ) -> None:
        """
        Убеждается, что город и правда взят и решать его судьбу вправе
        именно эта армия.

        Все проверки идут до единого изменения мира: отказ на середине
        оставил бы армию залоченной операцией, которой не существует.
        """
        if army.faction_id == owner.id:
            raise BorderTownResolutionInvalidError(
                town_id=town.id, reason="город принадлежит той же фракции"
            )
        if army.is_in_tactical_battle:
            raise BorderTownResolutionInvalidError(
                town_id=town.id, reason="армия связана тактическим боем"
            )
        if army.is_busy_with_operation:
            raise BorderTownResolutionInvalidError(
                town_id=town.id, reason="армия уже занята другой операцией"
            )
        if army.current_hex != town.center_hex:
            raise BorderTownResolutionInvalidError(
                town_id=town.id, reason="армия стоит не на гексе города"
            )

        garrison = world_state.get_garrison(town.zone_id)
        if garrison is not None and garrison.total_units_count > 0:
            raise BorderTownResolutionInvalidError(
                town_id=town.id, reason="гарнизон города еще держится"
            )

        # На гексе может остаться недобитое войско защитника - тогда город
        # еще не взят, каким бы пустым ни был его гарнизон
        defender = next(
            (
                other
                for other in world_state.get_armies_at_hex(town.center_hex)
                if other.faction_id == owner.id and not other.is_wiped_out
            ),
            None,
        )
        if defender is not None:
            raise BorderTownResolutionInvalidError(
                town_id=town.id,
                reason=f"город прикрывает войско защитника '{defender.name}'",
            )

        operation = world_state.get_town_operation(town.id)
        if operation is not None:
            raise BorderTownOperationInProgressError(
                town_id=town.id, resolution_type=operation.resolution_type.value
            )

    # ==================================================================
    # ШАГ ГЛОБАЛЬНОГО ТАКТА
    # ==================================================================

    async def process_town_resolutions(
        self, world_state: WorldState
    ) -> BorderTownResolutionStepReport:
        """
        Прожигает по такту у всех начатых операций и доводит до конца те,
        у которых отсчет дошел до нуля.

        Шаг идет в начале такта: добыча и новые земли должны попасть уже
        в эту экономику, а не ждать следующего хода.
        """
        report = BorderTownResolutionStepReport()

        for operation in list(world_state.border_town_operations.values()):
            if not operation.advance():
                continue

            world_state.remove_town_operation(operation.town_id)
            await self._apply_resolution_effect(world_state, operation, report)
            report.completed_operation_ids.append(operation.id)

        return report

    async def _apply_resolution_effect(
        self,
        world_state: WorldState,
        operation: BorderTownOperation,
        report: BorderTownResolutionStepReport,
    ) -> None:
        """
        Применяет итоговый эффект отработавшей операции.

        Армия освобождается в любом случае - даже если города за эти такты
        уже не стало (его добил кто-то другой): держать войско в плену у
        несуществующего поселения нельзя.
        """
        self._release_army(world_state, operation, report)

        found = world_state.find_border_town(operation.town_id)
        if found is None:
            return

        owner, town = found
        self._set_town_garrison_lock(world_state, town, locked=False)
        conqueror = world_state.get_faction(operation.conqueror_faction_id)

        if operation.resolution_type is BorderTownResolutionType.RAZE:
            await self._outcomes.raze(world_state, owner, town, conqueror, operation)
            report.razed_town_ids.append(town.id)
        elif operation.resolution_type is BorderTownResolutionType.PILLAGE:
            await self._outcomes.pillage(owner, town, conqueror, operation)
            report.pillaged_town_ids.append(town.id)
        elif operation.resolution_type is BorderTownResolutionType.OCCUPY:
            await self._outcomes.occupy(world_state, owner, town, conqueror, operation)
            report.occupied_town_ids.append(town.id)

    # ==================================================================
    # ЧТЕНИЕ
    # ==================================================================

    @staticmethod
    def get_town_operation(
        world_state: WorldState, town_id: str
    ) -> Optional[BorderTownOperation]:
        """
        Операция, которая идет над городом прямо сейчас, - прогресс для окна
        осады. None означает, что город никто не разоряет.

        Город при этом обязан существовать: спрашивать про судьбу
        несуществующего поселения - ошибка обращения, а не пустой ответ.
        """
        require_town_on_map(world_state, town_id)
        return world_state.get_town_operation(town_id)

    # ==================================================================
    # ВСПОМОГАТЕЛЬНОЕ
    # ==================================================================

    @staticmethod
    def _set_town_garrison_lock(
        world_state: WorldState, town: BorderTown, locked: bool
    ) -> None:
        """
        Замораживает (или отпускает) гарнизон города на время операции: пока
        победитель хозяйничает в стенах, ополчение не набирается и не лечится.
        """
        garrison = world_state.get_garrison(town.zone_id)
        if garrison is not None:
            garrison.is_locked_in_resolution = locked

    @staticmethod
    def _release_army(
        world_state: WorldState,
        operation: BorderTownOperation,
        report: BorderTownResolutionStepReport,
    ) -> None:
        """Снимает с армии победителя лок операции - она снова вольна идти."""
        army = world_state.get_army(operation.army_id)
        if army is None:
            return

        army.release_from_operation()
        report.released_army_ids.append(army.id)

    async def _publish_resolution_started(
        self,
        town: BorderTown,
        army: StrategicArmy,
        resolution_type: BorderTownResolutionType,
        operation: Optional[BorderTownOperation],
    ) -> None:
        """
        Объявляет о начале операции над городом.

        Пропуск (IGNORE) тоже объявляется, хотя операции за ним не стоит:
        решение победителя пройти мимо - такое же событие партии, как и
        решение сжечь поселение дотла.
        """
        if self._event_bus is None:
            return

        await self._event_bus.publish(
            GameEvents.Economy.BORDER_TOWN_RESOLUTION_STARTED,
            operation_id=None if operation is None else operation.id,
            town_id=town.id,
            town_name=town.name,
            army_id=army.id,
            conqueror_faction_id=army.faction_id,
            original_faction_id=town.faction_id,
            resolution_type=resolution_type.value,
            ticks_total=0 if operation is None else operation.ticks_total,
        )
