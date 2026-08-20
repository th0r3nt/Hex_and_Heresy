"""
Сервис управления экспедициями рабочих в нейтральные земли (караваны, добыча, доставка).
"""

from typing import Optional

from src.back.l01_domain.army.constants import StrategicMovementPace
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.exceptions import (
    InvalidAssignmentTargetError,
    WorkerNotAvailableError,
)
from src.back.l01_domain.factions.constants import (
    NEUTRAL_HEX_GOLD_BASE_YIELD_PER_UNIT,
    ResourceType,
    WorkerAssignmentStatus,
    WorkerAssignmentType,
)
from src.back.l01_domain.factions.models.workers import WorkerAssignment
from src.back.l01_domain.maps.models.strategic import HexCoordinates, hex_line
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.event.registry import GameEvents


class ExpeditionWorkerService:
    """
    Управляет экспедициями рабочих в опасные нейтральные земли:
    формирование каравана, пошаговый контроль фаз (марш туда -> добыча -> марш обратно -> разгрузка)
    и обработка гибели отряда.
    """

    def __init__(self, event_bus: Optional[EventBusProtocol] = None) -> None:
        self._event_bus = event_bus

    async def dispatch_expedition(
        self,
        world_state: WorldState,
        squad_id: str,
        faction_id: str,
        target_hex: HexCoordinates,
        home_hex: HexCoordinates,
        mining_duration_ticks: int,
    ) -> WorkerAssignment:
        """
        Формирует и отправляет караван рабочих в экспедицию на нейтральный гекс.
        Отряд рабочих отделяется в отдельную мобильную армию для физического движения по карте.
        """
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise InvalidAssignmentTargetError(faction_id, "фракция не найдена")

        if mining_duration_ticks < 1:
            raise InvalidAssignmentTargetError(
                str(mining_duration_ticks),
                "длительность добычи должна быть не менее одного такта",
            )

        # 1. Поиск и валидация отряда
        source_army = None
        squad = None
        for army in world_state.get_faction_armies(faction_id):
            for sq in army.squads:
                if sq.id == squad_id:
                    squad = sq
                    source_army = army
                    break
            if squad is not None:
                break

        if squad is None or source_army is None:
            raise WorkerNotAvailableError(squad_id, "отряд не найден в армиях фракции")

        if squad.archetype.tier != 0:
            raise WorkerNotAvailableError(
                squad_id, f"отряд имеет тир {squad.archetype.tier}, требуются рабочие (тир 0)"
            )

        if squad.state.unit_count <= 0:
            raise WorkerNotAvailableError(squad_id, "отряд полностью уничтожен")

        if source_army.is_in_tactical_battle:
            raise WorkerNotAvailableError(squad_id, "армия связана тактическим боем")

        existing_assignment = world_state.get_squad_assignment(squad_id)
        if existing_assignment is not None and existing_assignment.is_active:
            raise WorkerNotAvailableError(squad_id, "отряд уже выполняет другое назначение")

        # 2. Выделение отряда в отдельную армию-караван
        source_army.remove_squad(squad_id)

        path_to_target = hex_line(home_hex, target_hex)
        planned_path = path_to_target[1:] if len(path_to_target) > 1 else []

        caravan_army = StrategicArmy(
            faction_id=faction_id,
            name=f"Караван ({squad.display_name})",
            current_hex=home_hex,
            target_hex=target_hex,
            planned_path=planned_path,
            pace=StrategicMovementPace.MARCH,
        )
        caravan_army.add_squad(squad)
        world_state.add_army(caravan_army)

        # 3. Регистрация доменного назначения
        assignment = WorkerAssignment.create_expedition(
            squad_id=squad_id,
            faction_id=faction_id,
            target_hex=target_hex,
            home_hex=home_hex,
            mining_duration_ticks=mining_duration_ticks,
            expedition_army_id=caravan_army.id,
        )
        world_state.add_worker_assignment(assignment)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.EXPEDITION_DISPATCHED,
                assignment_id=assignment.id,
                squad_id=squad_id,
                faction_id=faction_id,
                army_id=caravan_army.id,
                target_hex=target_hex.to_axial(),
                duration_ticks=mining_duration_ticks,
            )

        return assignment

    async def process_expeditions(self, world_state: WorldState) -> list[str]:
        """
        Обрабатывает все активные экспедиции:
        - переход к добыче при прибытии на нейтральный гекс;
        - начисление груза за такт добычи на месте;
        - автоматический разворот каравана при окончании срока;
        - разгрузка ресурсов в казну фракции при возвращении домой.
        Возвращает список ID завершенных на этом такте экспедиций.
        """
        completed_expeditions: list[str] = []

        for assignment in list(world_state.worker_assignments.values()):
            if (
                assignment.assignment_type != WorkerAssignmentType.EXPEDITION
                or not assignment.is_active
            ):
                continue

            caravan_army = (
                world_state.get_army(assignment.expedition_army_id or "")
                if assignment.expedition_army_id
                else None
            )

            # Проверка гибели каравана
            if caravan_army is None or caravan_army.is_wiped_out:
                assignment.abort()
                if self._event_bus is not None:
                    await self._event_bus.publish(
                        GameEvents.Economy.EXPEDITION_LOST,
                        assignment_id=assignment.id,
                        squad_id=assignment.squad_id,
                        faction_id=assignment.faction_id,
                    )
                continue

            if caravan_army.is_in_tactical_battle:
                continue

            # Фаза 1: движение к цели
            if assignment.status == WorkerAssignmentStatus.TRAVELING_OUT:
                if (
                    caravan_army.current_hex == assignment.target_hex
                    and not caravan_army.planned_path
                ):
                    assignment.start_mining()
                    if self._event_bus is not None:
                        await self._event_bus.publish(
                            GameEvents.Economy.EXPEDITION_MINING_STARTED,
                            assignment_id=assignment.id,
                            squad_id=assignment.squad_id,
                            faction_id=assignment.faction_id,
                            target_hex=(
                                assignment.target_hex.to_axial()
                                if assignment.target_hex
                                else None
                            ),
                        )

            # Фаза 2: добыча на месте
            elif assignment.status == WorkerAssignmentStatus.MINING:
                squad = caravan_army.squads[0] if caravan_army.squads else None
                if squad is None or squad.state.unit_count <= 0:
                    assignment.abort()
                    continue

                gold_mined = NEUTRAL_HEX_GOLD_BASE_YIELD_PER_UNIT * squad.state.unit_count
                mined_res = {ResourceType.GOLD: gold_mined}

                finished_mining = assignment.tick_mining(mined_res)

                if finished_mining:
                    if assignment.target_hex and assignment.home_hex:
                        return_path = hex_line(assignment.target_hex, assignment.home_hex)
                        caravan_army.planned_path = (
                            return_path[1:] if len(return_path) > 1 else []
                        )
                        caravan_army.target_hex = assignment.home_hex

                    if self._event_bus is not None:
                        await self._event_bus.publish(
                            GameEvents.Economy.EXPEDITION_RETURNING,
                            assignment_id=assignment.id,
                            squad_id=assignment.squad_id,
                            faction_id=assignment.faction_id,
                            accumulated_gold=assignment.accumulated_cargo.get(
                                ResourceType.GOLD, 0.0
                            ),
                        )

            # Фаза 3: возвращение домой и разгрузка
            elif assignment.status == WorkerAssignmentStatus.TRAVELING_BACK:
                if (
                    caravan_army.current_hex == assignment.home_hex
                    and not caravan_army.planned_path
                ):
                    cargo = assignment.arrive_home()
                    faction = world_state.get_faction(assignment.faction_id)
                    if faction is not None:
                        for res_type, amount in cargo.items():
                            faction.earn(res_type, amount)

                    completed_expeditions.append(assignment.id)

                    if self._event_bus is not None:
                        await self._event_bus.publish(
                            GameEvents.Economy.EXPEDITION_RETURNED,
                            assignment_id=assignment.id,
                            squad_id=assignment.squad_id,
                            faction_id=assignment.faction_id,
                            delivered_cargo={k.value: v for k, v in cargo.items()},
                        )

        return completed_expeditions
