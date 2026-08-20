"""
Тесты сервиса экспедиций рабочих в нейтральные земли (формирование каравана, марш, добыча, возвращение).
"""

import pytest

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions import WorkerNotAvailableError
from src.back.l01_domain.factions.constants import (
    ResourceType,
    WorkerAssignmentStatus,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.movement import StrategicMovementService
from src.back.l02_services.turns.strategic.workers.expedition import (
    ExpeditionWorkerService,
)


@pytest.fixture
def goblin_workers() -> Squad:
    archetype = UnitArchetype(
        id="unit_goblins_00",
        race=FactionRace.GREENSKINS,
        faction_id="greenskins",
        name="Гоблины-рабы",
        tier=0,
        default_unit_count=100,
        base_stats=BaseUnitStats(max_hp=10.0),
        base_upkeep_food=1.0,
        base_upkeep_gold=0.0,
    )
    return Squad.create_new(archetype=archetype)


class TestExpeditionWorkerService:
    @pytest.mark.asyncio
    async def test_dispatch_expedition_creates_caravan_army(
        self, orc_faction, goblin_workers, fake_bus
    ):
        home_hex = HexCoordinates.from_axial(0, 0)
        target_hex = HexCoordinates.from_axial(2, 0)

        base_army = StrategicArmy(
            faction_id=orc_faction.id,
            current_hex=home_hex,
        )
        base_army.add_squad(goblin_workers)

        world = WorldState()
        world.add_faction(orc_faction)
        world.add_army(base_army)

        service = ExpeditionWorkerService(event_bus=fake_bus)
        assignment = await service.dispatch_expedition(
            world_state=world,
            squad_id=goblin_workers.id,
            faction_id=orc_faction.id,
            target_hex=target_hex,
            home_hex=home_hex,
            mining_duration_ticks=3,
        )

        assert assignment.status == WorkerAssignmentStatus.TRAVELING_OUT
        assert goblin_workers.id not in [s.id for s in base_army.squads]

        # Проверяем появление новой армии-каравана
        caravan_army = world.get_army(assignment.expedition_army_id or "")
        assert caravan_army is not None
        assert caravan_army.current_hex == home_hex
        assert caravan_army.target_hex == target_hex
        assert len(caravan_army.planned_path) > 0
        assert caravan_army.squads[0].id == goblin_workers.id

    @pytest.mark.asyncio
    async def test_cannot_dispatch_non_tier_0_squad(self, orc_faction, sample_army):
        world = WorldState()
        world.add_faction(orc_faction)
        world.add_army(sample_army)

        service = ExpeditionWorkerService()
        with pytest.raises(WorkerNotAvailableError):
            await service.dispatch_expedition(
                world_state=world,
                squad_id=sample_army.squads[0].id,
                faction_id=orc_faction.id,
                target_hex=HexCoordinates.from_axial(1, 0),
                home_hex=HexCoordinates.from_axial(0, 0),
                mining_duration_ticks=2,
            )

    @pytest.mark.asyncio
    async def test_full_expedition_lifecycle_integration(
        self, orc_faction, goblin_workers, fake_bus
    ):
        home_hex = HexCoordinates.from_axial(0, 0)
        target_hex = HexCoordinates.from_axial(2, 0)  # дистанция 2 гекса
        orc_faction.resources[ResourceType.GOLD] = 0.0

        base_army = StrategicArmy(faction_id=orc_faction.id, current_hex=home_hex)
        base_army.add_squad(goblin_workers)

        world = WorldState()
        world.add_faction(orc_faction)
        world.add_army(base_army)

        expedition_service = ExpeditionWorkerService(event_bus=fake_bus)
        movement_service = StrategicMovementService(event_bus=fake_bus)

        # 1. Отправляем караван на 2 такта добычи (скорость MARCH = 2 гекса за такт)
        assignment = await expedition_service.dispatch_expedition(
            world_state=world,
            squad_id=goblin_workers.id,
            faction_id=orc_faction.id,
            target_hex=target_hex,
            home_hex=home_hex,
            mining_duration_ticks=2,
        )
        caravan_army = world.get_army(assignment.expedition_army_id or "")
        assert caravan_army is not None

        # Такт 1: Движение к цели (проходит 2 гекса и встает на target_hex)
        await movement_service.process_movements_and_encounters(world)
        assert caravan_army.current_hex == target_hex

        # Экспедиционный сервис видит прибытие и переводит в MINING
        await expedition_service.process_expeditions(world)
        assert assignment.status == WorkerAssignmentStatus.MINING

        # Такт 2: Первый такт добычи на месте (+50 золота в буфер cargo)
        await expedition_service.process_expeditions(world)
        assert assignment.status == WorkerAssignmentStatus.MINING
        assert assignment.accumulated_cargo[ResourceType.GOLD] == 50.0
        assert orc_faction.resources[ResourceType.GOLD] == 0.0  # в казну еще не поступило

        # Такт 3: Второй такт добычи (финал срока, статус TRAVELING_BACK, построен обратный путь)
        await expedition_service.process_expeditions(world)
        assert assignment.status == WorkerAssignmentStatus.TRAVELING_BACK
        assert assignment.accumulated_cargo[ResourceType.GOLD] == 100.0
        assert len(caravan_army.planned_path) > 0

        # Такт 4: Движение каравана обратно на базу
        await movement_service.process_movements_and_encounters(world)
        assert caravan_army.current_hex == home_hex

        # Разгрузка ресурсов в казну
        completed = await expedition_service.process_expeditions(world)
        assert assignment.id in completed
        assert assignment.status == WorkerAssignmentStatus.COMPLETED
        assert orc_faction.resources[ResourceType.GOLD] == 100.0

    @pytest.mark.asyncio
    async def test_destroyed_caravan_aborts_assignment(
        self, orc_faction, goblin_workers, fake_bus
    ):
        home_hex = HexCoordinates.from_axial(0, 0)
        target_hex = HexCoordinates.from_axial(2, 0)

        base_army = StrategicArmy(faction_id=orc_faction.id, current_hex=home_hex)
        base_army.add_squad(goblin_workers)

        world = WorldState()
        world.add_faction(orc_faction)
        world.add_army(base_army)

        service = ExpeditionWorkerService(event_bus=fake_bus)
        assignment = await service.dispatch_expedition(
            world_state=world,
            squad_id=goblin_workers.id,
            faction_id=orc_faction.id,
            target_hex=target_hex,
            home_hex=home_hex,
            mining_duration_ticks=2,
        )

        # Уничтожаем армию каравана
        caravan_army = world.get_army(assignment.expedition_army_id or "")
        assert caravan_army is not None
        caravan_army.squads.clear()

        await service.process_expeditions(world)

        assert assignment.status == WorkerAssignmentStatus.ABORTED
        assert assignment.is_active is False
