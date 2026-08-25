"""
Тесты доменной модели назначений рабочих (WorkerAssignment) и реестра WorldState.
"""

import pytest

from src.back.l01_domain.exceptions.workers import ExpeditionRecallForbiddenError
from src.back.l01_domain.factions.constants import (
    ResourceType,
    WorkerAssignmentStatus,
    WorkerAssignmentType,
)
from src.back.l01_domain.factions.models.workers import WorkerAssignment
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState


class TestStationaryWorkerAssignment:
    def test_create_stationary_immediate(self):
        assignment = WorkerAssignment.create_stationary(
            squad_id="squad_peasants_1",
            faction_id="humans",
            building_id="building_farm_1",
            needs_warmup=False,
        )

        assert assignment.assignment_type == WorkerAssignmentType.STATIONARY
        assert assignment.status == WorkerAssignmentStatus.WORKING
        assert assignment.warmup_ticks_remaining == 0
        assert assignment.is_active is True

    def test_create_stationary_with_warmup(self):
        assignment = WorkerAssignment.create_stationary(
            squad_id="squad_peasants_2",
            faction_id="humans",
            building_id="building_allied_mine",
            needs_warmup=True,
        )

        assert assignment.status == WorkerAssignmentStatus.WARMING_UP
        assert assignment.warmup_ticks_remaining == 1

        # Продвижение разогрева
        transitioned = assignment.advance_warmup()
        assert transitioned is True
        assert assignment.status == WorkerAssignmentStatus.WORKING
        assert assignment.warmup_ticks_remaining == 0

    def test_manual_unassign_allowed(self):
        assignment = WorkerAssignment.create_stationary(
            squad_id="squad_1",
            faction_id="humans",
            building_id="b_1",
        )
        # Не должно вызывать исключений
        assignment.assert_can_unassign_manually()
        assignment.abort()
        assert assignment.status == WorkerAssignmentStatus.ABORTED
        assert assignment.is_active is False


class TestExpeditionWorkerAssignment:
    def test_expedition_lifecycle(self):
        home = HexCoordinates.from_axial(0, 0)
        target = HexCoordinates.from_axial(3, -1)

        assignment = WorkerAssignment.create_expedition(
            squad_id="squad_goblins_1",
            faction_id="greenskins",
            target_hex=target,
            home_hex=home,
            mining_duration_ticks=2,
            expedition_army_id="army_caravan_1",
        )

        assert assignment.assignment_type == WorkerAssignmentType.EXPEDITION
        assert assignment.status == WorkerAssignmentStatus.TRAVELING_OUT
        assert assignment.mining_ticks_remaining == 2

        # 1. Прибытие на нейтральный гекс
        assignment.start_mining()
        assert assignment.status == WorkerAssignmentStatus.MINING

        # 2. Первый такт добычи
        finished = assignment.tick_mining({ResourceType.GOLD: 50.0})
        assert finished is False
        assert assignment.status == WorkerAssignmentStatus.MINING
        assert assignment.accumulated_cargo[ResourceType.GOLD] == 50.0
        assert assignment.mining_ticks_remaining == 1

        # 3. Второй такт добычи (завершение добычи и разворот каравана)
        finished = assignment.tick_mining({ResourceType.GOLD: 50.0})
        assert finished is True
        assert assignment.status == WorkerAssignmentStatus.TRAVELING_BACK
        assert assignment.accumulated_cargo[ResourceType.GOLD] == 100.0
        assert assignment.mining_ticks_remaining == 0

        # 4. Прибытие домой и разгрузка
        delivered_cargo = assignment.arrive_home()
        assert delivered_cargo[ResourceType.GOLD] == 100.0
        assert assignment.status == WorkerAssignmentStatus.COMPLETED
        assert assignment.is_active is False

    def test_expedition_cannot_be_recalled_manually(self):
        assignment = WorkerAssignment.create_expedition(
            squad_id="squad_1",
            faction_id="greenskins",
            target_hex=HexCoordinates.from_axial(1, 1),
            home_hex=HexCoordinates.from_axial(0, 0),
            mining_duration_ticks=3,
            expedition_army_id="army_1",
        )
        assignment.start_mining()

        with pytest.raises(ExpeditionRecallForbiddenError):
            assignment.assert_can_unassign_manually()


class TestWorldStateWorkerRegistry:
    def test_world_state_assignment_queries_and_cleanup(self):
        world = WorldState()

        a1 = WorkerAssignment.create_stationary(
            squad_id="sq_1", faction_id="humans", building_id="b_1"
        )
        a2 = WorkerAssignment.create_stationary(
            squad_id="sq_2", faction_id="humans", building_id="b_1"
        )
        a3 = WorkerAssignment.create_stationary(
            squad_id="sq_3", faction_id="orcs", building_id="b_2"
        )

        world.add_worker_assignment(a1)
        world.add_worker_assignment(a2)
        world.add_worker_assignment(a3)

        assert world.get_squad_assignment("sq_1") == a1
        assert len(world.get_building_assignments("b_1")) == 2
        assert len(world.get_faction_worker_assignments("humans")) == 2

        # Завершаем одно назначение и чистим реестр
        a1.abort()
        cleaned = world.cleanup_completed_assignments()

        assert len(cleaned) == 1
        assert cleaned[0].id == a1.id
        assert world.get_squad_assignment("sq_1") is None
        assert len(world.get_building_assignments("b_1")) == 1
