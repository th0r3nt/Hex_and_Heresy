"""
Тесты сервиса экономики, содержания армий, дефицита и строительства.
"""

import pytest

from src.back.l01_domain.army.constants import StrategicMovementPace
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import BuildingCategory, ResourceType
from src.back.l01_domain.factions.models.buildings import Building, ConstructedBuilding
from src.back.l01_domain.maps.constants import TerritoryZoneType
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.economy import StrategicEconomyService
from src.back.l02_services.turns.strategic.workers.stationary import (
    StationaryWorkerService,
)


class TestStrategicEconomyService:
    @pytest.mark.asyncio
    async def test_construction_progress_completion(self, human_faction, fake_bus):
        building_tmpl = Building(
            id="b_barracks",
            faction_id=human_faction.id,
            name="Городские казармы",
            category=BuildingCategory.MILITARY,
            allowed_zone=TerritoryZoneType.ALLIED_LANDS,
            construction_ticks=1,
        )
        constructed = ConstructedBuilding(
            building=building_tmpl,
            zone_id="zone_01",
            is_under_construction=True,
            construction_ticks_remaining=1,
        )
        human_faction.add_building(constructed)

        world_state = WorldState()
        world_state.add_faction(human_faction)

        service = StrategicEconomyService(event_bus=fake_bus)
        reports = await service.process_factions_economy(world_state)

        report = reports[human_faction.id]
        assert "Городские казармы" in report.completed_building_names
        assert constructed.is_under_construction is False

    @pytest.mark.asyncio
    async def test_upkeep_deduction_and_deficit_handling(
        self, human_faction, sample_army, fake_bus
    ):
        # Казна пуста: за такт в нее упадет только налог с цитадели (30 золота)
        human_faction.resources[ResourceType.GOLD] = 0.0
        human_faction.resources[ResourceType.FOOD] = 200.0

        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_army(sample_army)

        service = StrategicEconomyService(event_bus=fake_bus)
        reports = await service.process_factions_economy(world_state)

        report = reports[human_faction.id]
        assert report.tax_income_gold == 30.0
        assert report.upkeep_gold_required == 50.0
        assert report.upkeep_food_required == 100.0
        assert report.gold_deficit == 20.0
        assert report.food_deficit == 0.0
        assert human_faction.resources[ResourceType.GOLD] == 0.0
        assert human_faction.resources[ResourceType.FOOD] == 100.0

        squad = sample_army.squads[0]
        assert squad.state.morale < 50.0

    @pytest.mark.asyncio
    async def test_famine_triggers_squad_desertion(self, human_faction, sample_army, fake_bus):
        human_faction.resources[ResourceType.GOLD] = 500.0
        human_faction.resources[ResourceType.FOOD] = 0.0

        sample_army.squads[0].state.morale = 20.0
        sample_army.squads[0].state.is_in_panic = True

        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_army(sample_army)

        service = StrategicEconomyService(event_bus=fake_bus)
        reports = await service.process_factions_economy(world_state)

        report = reports[human_faction.id]
        assert len(report.deserted_squad_names) == 1
        assert len(sample_army.squads) == 0

    @pytest.mark.asyncio
    async def test_stationary_building_production(self, human_faction, fake_bus):
        peasant_archetype = UnitArchetype(
            id="unit_peasants",
            race=FactionRace.HUMANS,
            faction_id=human_faction.id,
            name="Крепостные",
            tier=0,
            default_unit_count=100,
            base_stats=BaseUnitStats(max_hp=10.0),
        )
        peasant_squad = Squad.create_new(archetype=peasant_archetype)

        building_tmpl = Building(
            id="b_wheat_fields",
            faction_id=human_faction.id,
            name="Пшеничные угодья",
            category=BuildingCategory.ECONOMIC,
            allowed_zone=TerritoryZoneType.BASE,
            requires_workers=True,
            resource_output_per_worker={ResourceType.FOOD: 60.0},
        )
        farm = ConstructedBuilding(
            building=building_tmpl,
            zone_id="base",
            is_under_construction=False,
        )
        human_faction.add_building(farm)

        army = StrategicArmy(
            faction_id=human_faction.id,
            current_hex=HexCoordinates.from_axial(0, 0),
            pace=StrategicMovementPace.MARCH,
        )
        army.add_squad(peasant_squad)

        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_army(army)

        worker_service = StationaryWorkerService(event_bus=fake_bus)
        await worker_service.assign_squad_to_building(
            world_state=world_state,
            squad_id=peasant_squad.id,
            faction_id=human_faction.id,
            building_id=farm.id,
        )

        econ_service = StrategicEconomyService(event_bus=fake_bus)
        reports = await econ_service.process_factions_economy(world_state)

        report = reports[human_faction.id]
        assert report.income_food == 60.0
