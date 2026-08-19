"""
Тесты сервиса экономики, содержания армий, дефицита и строительства.
"""

import pytest

from src.back.l01_domain.factions.constants import (
    BuildingCategory,
    ResourceType,
    WorkerRiskTier,
)
from src.back.l01_domain.factions.models.buildings import Building, ConstructedBuilding
from src.back.l01_domain.maps.constants import TerritoryZoneType
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.economy import StrategicEconomyService


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
        # 100 бойцов: золото 50.0, еда 100.0
        human_faction.resources[ResourceType.GOLD] = 30.0  # дефицит 20.0
        human_faction.resources[ResourceType.FOOD] = 200.0  # хватает

        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_army(sample_army)

        service = StrategicEconomyService(event_bus=fake_bus)
        reports = await service.process_factions_economy(world_state)

        report = reports[human_faction.id]
        assert report.upkeep_gold_required == 50.0
        assert report.upkeep_food_required == 100.0
        assert report.gold_deficit == 20.0
        assert report.food_deficit == 0.0
        assert human_faction.resources[ResourceType.GOLD] == 0.0
        assert human_faction.resources[ResourceType.FOOD] == 100.0

        # Проверяем штраф к морали за дефицит золота
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
    async def test_worker_income_by_risk_tier(self, human_faction, sample_army, fake_bus):
        # Превращаем отряд в рабочих (тир 0)
        sample_army.squads[0] = sample_army.squads[0].model_copy(
            update={
                "archetype": sample_army.squads[0].archetype.model_copy(update={"tier": 0})
            }
        )
        human_faction.resources[ResourceType.GOLD] = 0.0
        human_faction.resources[ResourceType.FOOD] = 500.0

        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_army(sample_army)

        service = StrategicEconomyService(event_bus=fake_bus)
        assignments = {human_faction.id: WorkerRiskTier.HIGH}
        reports = await service.process_factions_economy(
            world_state, worker_assignments=assignments
        )

        report = reports[human_faction.id]
        assert report.income_gold == 50.0
