"""
Сервис назначения и снятия рабочих со стационарных зданий на базе и в союзных землях.
"""

from typing import Optional

from src.back.l01_domain.exceptions.workers import (
    InvalidAssignmentTargetError,
    WorkerNotAvailableError,
)
from src.back.l01_domain.factions.models.workers import WorkerAssignment
from src.back.l01_domain.maps.models.strategic import hex_zone_id
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.event.registry import GameEvents


class StationaryWorkerService:
    """
    Управляет жизненным циклом стационарных рабочих:
    валидация доступности отряда, привязка к слотам здания, мгновенное освобождение.
    """

    def __init__(self, event_bus: Optional[EventBusProtocol] = None) -> None:
        self._event_bus = event_bus

    async def assign_squad_to_building(
        self,
        world_state: WorldState,
        squad_id: str,
        faction_id: str,
        building_id: str,
    ) -> WorkerAssignment:
        """
        Назначает отряд рабочих (тир 00) на экономическое здание.
        Если отряд дислоцирован в том же гексе, что и здание - приступает к работе сразу (working).
        Если отряд находится в другом гексе - выставляется разогрев на 1 такт (warming_up).
        """
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise InvalidAssignmentTargetError(faction_id, "фракция не найдена")

        # 1. Поиск здания
        constructed_building = next(
            (b for b in faction.buildings if b.id == building_id), None
        )
        if constructed_building is None:
            raise InvalidAssignmentTargetError(
                building_id, "здание не найдено у данной фракции"
            )

        if constructed_building.is_under_construction:
            raise InvalidAssignmentTargetError(building_id, "здание еще строится")

        if not constructed_building.building.requires_workers:
            raise InvalidAssignmentTargetError(
                building_id, "здание не требует назначения рабочих"
            )

        # 2. Поиск отряда в армиях фракции
        squad = None
        squad_army = None
        for army in world_state.get_faction_armies(faction_id):
            for sq in army.squads:
                if sq.id == squad_id:
                    squad = sq
                    squad_army = army
                    break
            if squad is not None:
                break

        if squad is None or squad_army is None:
            raise WorkerNotAvailableError(
                squad_id, "отряд не найден в действующих армиях фракции"
            )

        if squad.archetype.tier != 0:
            raise WorkerNotAvailableError(
                squad_id, f"отряд имеет тир {squad.archetype.tier}, требуются рабочие (тир 0)"
            )

        if squad.state.unit_count <= 0:
            raise WorkerNotAvailableError(squad_id, "отряд полностью уничтожен")

        if squad_army.is_in_tactical_battle:
            raise WorkerNotAvailableError(squad_id, "армия отряда связана тактическим боем")

        # 3. Проверка на наличие уже активного назначения
        existing_assignment = world_state.get_squad_assignment(squad_id)
        if existing_assignment is not None and existing_assignment.is_active:
            raise WorkerNotAvailableError(squad_id, "отряд уже выполняет другое назначение")

        # 4. Проверка пространственной привязки (разогрев)
        army_zone_id = hex_zone_id(squad_army.current_hex)
        needs_warmup = (
            constructed_building.zone_id != army_zone_id
            and constructed_building.zone_id != "base"
        )

        assignment = WorkerAssignment.create_stationary(
            squad_id=squad_id,
            faction_id=faction_id,
            building_id=building_id,
            needs_warmup=needs_warmup,
        )

        world_state.add_worker_assignment(assignment)
        if squad_id not in constructed_building.assigned_worker_squad_ids:
            constructed_building.assigned_worker_squad_ids.append(squad_id)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.WORKER_ASSIGNED,
                assignment_id=assignment.id,
                squad_id=squad_id,
                faction_id=faction_id,
                building_id=building_id,
                status=assignment.status.value,
            )

        return assignment

    async def unassign_squad_from_building(
        self,
        world_state: WorldState,
        squad_id: str,
    ) -> None:
        """
        Мгновенно снимает рабочего с производства и возвращает отряд в свободный пул.
        """
        assignment = world_state.get_squad_assignment(squad_id)
        if assignment is None:
            return

        assignment.assert_can_unassign_manually()

        # Удаляем отряд из списков рабочих зданий
        if assignment.target_building_id is not None:
            faction = world_state.get_faction(assignment.faction_id)
            if faction is not None:
                building = next(
                    (b for b in faction.buildings if b.id == assignment.target_building_id),
                    None,
                )
                if building is not None and squad_id in building.assigned_worker_squad_ids:
                    building.assigned_worker_squad_ids.remove(squad_id)

        assignment.abort()

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.WORKER_UNASSIGNED,
                assignment_id=assignment.id,
                squad_id=squad_id,
                faction_id=assignment.faction_id,
            )
