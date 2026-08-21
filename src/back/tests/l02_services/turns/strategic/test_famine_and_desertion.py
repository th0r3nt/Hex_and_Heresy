"""
Тесты краевых случаев экономической системы: банкротство, дефицит провизии,
штрафы морали, дезертирство паникующих отрядов и завершение строек.
"""

import pytest

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.characters.commanders import (
    Commander,
    CommanderArchetype,
    CommanderArchetypeStats,
    CommanderCharacteristics,
    CommanderGenerationType,
    CommanderTrait,
)
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
from src.back.utils.event.registry import GameEvents


@pytest.fixture
def peasant_squad() -> Squad:
    archetype = UnitArchetype(
        id="unit_peasants_econ",
        race=FactionRace.HUMANS,
        name="Крепостные",
        tier=0,
        default_unit_count=100,
        base_stats=BaseUnitStats(max_hp=10.0, base_morale=50.0),
        base_upkeep_food=1.0,
        base_upkeep_gold=0.0,
    )
    return Squad.create_new(archetype=archetype)


class TestFamineAndDeficitConsequences:
    @pytest.mark.asyncio
    async def test_gold_deficit_only_penalizes_morale_without_desertion(
        self, human_faction, sample_army, fake_bus
    ):
        # Есть провизия, но 0 золота
        human_faction.resources[ResourceType.GOLD] = 0.0
        human_faction.resources[ResourceType.FOOD] = 500.0

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(sample_army)

        service = StrategicEconomyService(event_bus=fake_bus)
        reports = await service.process_factions_economy(world)

        report = reports[human_faction.id]
        assert report.gold_deficit > 0.0
        assert report.food_deficit == 0.0
        # При отсутствии дефицита еды дезертирство не наступает
        assert len(report.deserted_squad_names) == 0
        assert len(sample_army.squads) == 1
        # Моральный штраф за невыплату жалования (-10)
        assert sample_army.squads[0].state.morale == 40.0

    @pytest.mark.asyncio
    async def test_minor_food_deficit_under_fifty_percent_causes_no_desertion(
        self, human_faction, sample_army, fake_bus
    ):
        # Требуется 100 еды. В казне есть 60 еды -> дефицит 40 еды (40% < 50%)
        human_faction.resources[ResourceType.GOLD] = 500.0
        human_faction.resources[ResourceType.FOOD] = 60.0

        sample_army.squads[0].state.morale = 25.0  # Низкая мораль

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(sample_army)

        service = StrategicEconomyService(event_bus=fake_bus)
        reports = await service.process_factions_economy(world)

        report = reports[human_faction.id]
        assert report.food_deficit == 40.0
        # Дефицит меньше 50% от нормы — отряд терпит лишения, но не дезертирует
        assert len(report.deserted_squad_names) == 0
        assert len(sample_army.squads) == 1

    @pytest.mark.asyncio
    async def test_critical_famine_causes_panicking_squad_to_desert_and_aborts_work(
        self, human_faction, peasant_squad, fake_bus
    ):
        human_faction.resources[ResourceType.GOLD] = 0.0
        human_faction.resources[ResourceType.FOOD] = 0.0

        # Отряд рабочих в панике
        peasant_squad.state.morale = 15.0
        peasant_squad.state.is_in_panic = True

        farm_tmpl = Building(
            id="b_wheat_farm",
            faction_id=human_faction.id,
            name="Ферма",
            category=BuildingCategory.ECONOMIC,
            allowed_zone=TerritoryZoneType.BASE,
            requires_workers=True,
            resource_output_per_worker={
                ResourceType.FOOD: 10.0
            },  # Доход 10 еды при расходе 100 -> дефицит 90 > 50
        )
        farm = ConstructedBuilding(
            building=farm_tmpl, zone_id="base", is_under_construction=False
        )
        human_faction.add_building(farm)

        army = StrategicArmy(
            faction_id=human_faction.id, current_hex=HexCoordinates.from_axial(0, 0)
        )
        army.add_squad(peasant_squad)

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(army)

        # Назначаем рабочего на ферму
        worker_service = StationaryWorkerService(event_bus=fake_bus)
        assignment = await worker_service.assign_squad_to_building(
            world_state=world,
            squad_id=peasant_squad.id,
            faction_id=human_faction.id,
            building_id=farm.id,
        )
        assert assignment.is_active is True

        # Запуск экономического такта в условиях тотального голода
        econ_service = StrategicEconomyService(event_bus=fake_bus)
        reports = await econ_service.process_factions_economy(world)

        report = reports[human_faction.id]
        assert "Крепостные" in report.deserted_squad_names
        assert len(army.squads) == 0
        # Назначение дезертировавшего рабочего автоматически прервано
        assert assignment.is_active is False
        assert assignment.status.value == "aborted"

        event_names = [name for name, _ in fake_bus.events]
        assert GameEvents.Economy.FAMINE_OCCURRED in event_names
        assert GameEvents.Economy.SQUAD_DESERTED in event_names

    @pytest.mark.asyncio
    async def test_commander_upkeep_multiplier_increases_gold_expense(
        self, human_faction, sample_army, fake_bus
    ):
        # Полководец с архетипом жадности (+30% к расходам на войско)
        greedy_commander = Commander(
            name="Жадный Барон",
            faction_id=human_faction.id,
            generation_type=CommanderGenerationType.PROCEDURAL,
            archetype=CommanderArchetype(
                id="arch_greedy",
                name="Жадный",
                description="...",
                stats=CommanderArchetypeStats(upkeep_gold_modifier=1.3),
            ),
            trait=CommanderTrait(id="trait_gold", name="Сребролюбец", text_fragment="..."),
            characteristics=CommanderCharacteristics(),
        )
        sample_army.commander = greedy_commander
        # Базовое содержание отряда: 50 золота -> с полководцем: 50 * 1.3 = 65 золота
        assert sample_army.total_upkeep_gold == pytest.approx(65.0)

        human_faction.resources[ResourceType.GOLD] = 100.0
        human_faction.resources[ResourceType.FOOD] = 200.0

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(sample_army)

        service = StrategicEconomyService(event_bus=fake_bus)
        reports = await service.process_factions_economy(world)

        report = reports[human_faction.id]
        assert report.upkeep_gold_required == pytest.approx(65.0)
        assert human_faction.resources[ResourceType.GOLD] == pytest.approx(35.0)


class TestFamineAffectsAllArmiesNotJustFirst:
    @pytest.mark.asyncio
    async def test_critical_famine_causes_desertion_in_every_affected_army(
        self, human_faction, fake_bus
    ):
        """
        Баг: `break` в конце цикла по армиям прерывал обработку дезертирства
        сразу после первой найденной армии с паникующим отрядом — остальные
        армии той же фракции в этот такт не затрагивались вовсе, даже если
        в них тоже были паникующие/деморализованные отряды.
        """
        human_faction.resources[ResourceType.GOLD] = 0.0
        human_faction.resources[ResourceType.FOOD] = 0.0

        def make_panicking_army(suffix: str) -> StrategicArmy:
            archetype = UnitArchetype(
                id=f"unit_peasants_{suffix}",
                race=FactionRace.HUMANS,
                name="Крепостные",
                tier=0,
                default_unit_count=100,
                base_stats=BaseUnitStats(max_hp=10.0, base_morale=50.0),
                base_upkeep_food=1.0,
                base_upkeep_gold=0.0,
            )
            squad = Squad.create_new(archetype=archetype)
            squad.state.morale = 15.0
            squad.state.is_in_panic = True

            army = StrategicArmy(
                faction_id=human_faction.id, current_hex=HexCoordinates.from_axial(0, 0)
            )
            army.add_squad(squad)
            return army

        army_1 = make_panicking_army("a")
        army_2 = make_panicking_army("b")

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(army_1)
        world.add_army(army_2)

        service = StrategicEconomyService(event_bus=fake_bus)
        reports = await service.process_factions_economy(world)

        report = reports[human_faction.id]
        # обе армии теряют по своему паникующему отряду, а не только первая
        assert len(report.deserted_squad_names) == 2
        assert len(army_1.squads) == 0
        assert len(army_2.squads) == 0
