"""
Тесты сервиса стационарных рабочих (назначение, разогрев, снятие с производства).
"""

import pytest

from src.back.l01_domain.army.constants import StrategicMovementPace
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions import (
    InvalidAssignmentTargetError,
    WorkerNotAvailableError,
)
from src.back.l01_domain.factions.constants import (
    BuildingCategory,
    ResourceType,
    WorkerAssignmentStatus,
)
from src.back.l01_domain.factions.models.buildings import Building, ConstructedBuilding
from src.back.l01_domain.maps.constants import TerritoryZoneType
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.economy import StrategicEconomyService
from src.back.l02_services.turns.strategic.workers.stationary import (
    StationaryWorkerService,
)


@pytest.fixture
def peasant_squad() -> Squad:
    archetype = UnitArchetype(
        id="unit_peasants_00",
        race=FactionRace.HUMANS,
        faction_id="humans",
        name="Крепостные",
        tier=0,
        default_unit_count=100,
        base_stats=BaseUnitStats(max_hp=10.0),
        base_upkeep_food=1.0,
        base_upkeep_gold=0.0,
    )
    return Squad.create_new(archetype=archetype)


@pytest.fixture
def gold_mine(human_faction) -> ConstructedBuilding:
    tmpl = Building(
        id="b_gold_mine",
        faction_id=human_faction.id,
        name="Золотой рудник",
        category=BuildingCategory.ECONOMIC,
        allowed_zone=TerritoryZoneType.ALLIED_LANDS,
        requires_workers=True,
        resource_output_per_worker={ResourceType.GOLD: 25.0},
    )
    b = ConstructedBuilding(
        building=tmpl,
        zone_id="0,0",
        is_under_construction=False,
    )
    human_faction.add_building(b)
    return b


class TestStationaryWorkerService:
    @pytest.mark.asyncio
    async def test_assign_immediate_working_in_same_zone(
        self, human_faction, peasant_squad, gold_mine, fake_bus
    ):
        army = StrategicArmy(
            faction_id=human_faction.id,
            current_hex=HexCoordinates.from_axial(0, 0),
            pace=StrategicMovementPace.MARCH,
        )
        army.add_squad(peasant_squad)

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(army)

        service = StationaryWorkerService(event_bus=fake_bus)
        assignment = await service.assign_squad_to_building(
            world_state=world,
            squad_id=peasant_squad.id,
            faction_id=human_faction.id,
            building_id=gold_mine.id,
        )

        assert assignment.status == WorkerAssignmentStatus.WORKING
        assert peasant_squad.id in gold_mine.assigned_worker_squad_ids

    @pytest.mark.asyncio
    async def test_assign_with_warmup_in_different_zone(
        self, human_faction, peasant_squad, gold_mine, fake_bus
    ):
        # Армия находится в гексе (2, 0), а шахта в (0, 0)
        army = StrategicArmy(
            faction_id=human_faction.id,
            current_hex=HexCoordinates.from_axial(2, 0),
        )
        army.add_squad(peasant_squad)

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(army)

        service = StationaryWorkerService(event_bus=fake_bus)
        assignment = await service.assign_squad_to_building(
            world_state=world,
            squad_id=peasant_squad.id,
            faction_id=human_faction.id,
            building_id=gold_mine.id,
        )

        assert assignment.status == WorkerAssignmentStatus.WARMING_UP
        assert assignment.warmup_ticks_remaining == 1

    @pytest.mark.asyncio
    async def test_cannot_assign_non_tier_0_squad(self, human_faction, sample_army, gold_mine):
        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(sample_army)  # В sample_army отряд тира 1

        service = StationaryWorkerService()
        with pytest.raises(WorkerNotAvailableError):
            await service.assign_squad_to_building(
                world_state=world,
                squad_id=sample_army.squads[0].id,
                faction_id=human_faction.id,
                building_id=gold_mine.id,
            )

    @pytest.mark.asyncio
    async def test_cannot_assign_building_under_construction(
        self, human_faction, peasant_squad, gold_mine
    ):
        gold_mine.is_under_construction = True
        army = StrategicArmy(
            faction_id=human_faction.id, current_hex=HexCoordinates.from_axial(0, 0)
        )
        army.add_squad(peasant_squad)

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(army)

        service = StationaryWorkerService()
        with pytest.raises(InvalidAssignmentTargetError):
            await service.assign_squad_to_building(
                world_state=world,
                squad_id=peasant_squad.id,
                faction_id=human_faction.id,
                building_id=gold_mine.id,
            )

    @pytest.mark.asyncio
    async def test_unassign_instantly_frees_squad(
        self, human_faction, peasant_squad, gold_mine, fake_bus
    ):
        army = StrategicArmy(
            faction_id=human_faction.id, current_hex=HexCoordinates.from_axial(0, 0)
        )
        army.add_squad(peasant_squad)

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(army)

        service = StationaryWorkerService(event_bus=fake_bus)
        await service.assign_squad_to_building(
            world_state=world,
            squad_id=peasant_squad.id,
            faction_id=human_faction.id,
            building_id=gold_mine.id,
        )

        assert peasant_squad.id in gold_mine.assigned_worker_squad_ids

        await service.unassign_squad_from_building(world, peasant_squad.id)

        assert peasant_squad.id not in gold_mine.assigned_worker_squad_ids
        assert world.get_squad_assignment(peasant_squad.id) is None


class TestStationaryEconomyIntegration:
    @pytest.mark.asyncio
    async def test_warmup_delays_income_by_one_tick(
        self, human_faction, peasant_squad, gold_mine, fake_bus
    ):
        # Стартовая казна: 0 золота
        human_faction.resources[ResourceType.GOLD] = 0.0
        army = StrategicArmy(
            faction_id=human_faction.id, current_hex=HexCoordinates.from_axial(2, 0)
        )
        army.add_squad(peasant_squad)

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(army)

        worker_service = StationaryWorkerService(event_bus=fake_bus)
        await worker_service.assign_squad_to_building(
            world_state=world,
            squad_id=peasant_squad.id,
            faction_id=human_faction.id,
            building_id=gold_mine.id,
        )

        econ_service = StrategicEconomyService(event_bus=fake_bus)

        # Такт 1: разогрев (дохода еще нет)
        reports_tick1 = await econ_service.process_factions_economy(world)
        assert reports_tick1[human_faction.id].income_gold == 0.0
        assert human_faction.resources[ResourceType.GOLD] == 0.0

        # Такт 2: разогрев завершен, пошла активная добыча (+25 золота)
        reports_tick2 = await econ_service.process_factions_economy(world)
        assert reports_tick2[human_faction.id].income_gold == 25.0
        assert human_faction.resources[ResourceType.GOLD] == 25.0
