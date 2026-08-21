"""
Сквозной End-to-End интеграционный тест полного цикла стратегической карты (5 тактов):
продвижение времени -> смена световых фаз суток -> стройка зданий ->
стационарная добыча -> караванная экспедиция -> генерация столкновений и засад.
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
from src.back.l01_domain.world.models.battleground import BattlefieldLootSite
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.orchestrator import (
    StrategicTurnOrchestrator,
)
from src.back.l02_services.turns.strategic.workers.expedition import (
    ExpeditionWorkerService,
)
from src.back.l02_services.turns.strategic.workers.stationary import (
    StationaryWorkerService,
)


class FakeEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args, **kwargs) -> None:
        self.published.append((event_name, kwargs))


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


class TestStrategicLifecycleE2E:
    @pytest.mark.asyncio
    async def test_five_ticks_campaign_simulation(self, human_faction, orc_faction, fake_bus):
        orchestrator = StrategicTurnOrchestrator(event_bus=fake_bus)
        stationary_service = StationaryWorkerService(event_bus=fake_bus)
        expedition_service = ExpeditionWorkerService(event_bus=fake_bus)

        # Ордынской фракции нужен запас провизии для снабжения каравана в течение 5 тактов
        orc_faction.resources[ResourceType.FOOD] = 500.0
        orc_faction.resources[ResourceType.GOLD] = 100.0

        world = WorldState()
        world.add_faction(human_faction)
        world.add_faction(orc_faction)

        # Центр карты (Ничья земля)
        neutral_hex = HexCoordinates.from_axial(3, 0)
        target_mine_hex = HexCoordinates.from_axial(4, 0)
        world.neutral_hexes.extend([neutral_hex, target_mine_hex])

        # 1. Создаем здание в процессе стройки у Людей (стройка 2 такта)
        barracks_tmpl = Building(
            id="b_barracks_e2e",
            faction_id=human_faction.id,
            name="Казармы легиона",
            category=BuildingCategory.MILITARY,
            allowed_zone=TerritoryZoneType.BASE,
            construction_ticks=2,
        )
        barracks = ConstructedBuilding(
            building=barracks_tmpl,
            zone_id="base",
            is_under_construction=True,
            construction_ticks_remaining=2,
        )
        human_faction.add_building(barracks)

        # 2. Создаем готовую ферму и назначаем отряд крестьян
        farm_tmpl = Building(
            id="b_farm_e2e",
            faction_id=human_faction.id,
            name="Пшеничные поля",
            category=BuildingCategory.ECONOMIC,
            allowed_zone=TerritoryZoneType.BASE,
            requires_workers=True,
            resource_output_per_worker={ResourceType.FOOD: 80.0},
        )
        farm = ConstructedBuilding(
            building=farm_tmpl, zone_id="base", is_under_construction=False
        )
        human_faction.add_building(farm)

        peasants_arch = UnitArchetype(
            id="unit_peasants_e2e",
            race=FactionRace.HUMANS,
            faction_id=human_faction.id,
            name="Крестьяне",
            tier=0,
            default_unit_count=100,
            base_stats=BaseUnitStats(max_hp=10.0),
        )
        peasants = Squad.create_new(archetype=peasants_arch)

        human_home_hex = HexCoordinates.from_axial(0, 0)
        human_base_army = StrategicArmy(
            faction_id=human_faction.id, current_hex=human_home_hex
        )
        human_base_army.add_squad(peasants)
        world.add_army(human_base_army)

        # Назначаем крестьян на ферму
        await stationary_service.assign_squad_to_building(
            world_state=world,
            squad_id=peasants.id,
            faction_id=human_faction.id,
            building_id=farm.id,
        )

        # 3. Отправляем ордынский караван в экспедицию на target_mine_hex
        goblins_arch = UnitArchetype(
            id="unit_goblins_e2e",
            race=FactionRace.GREENSKINS,
            faction_id=orc_faction.id,
            name="Гоблины-рудокопы",
            tier=0,
            default_unit_count=100,
            base_stats=BaseUnitStats(max_hp=10.0),
        )
        goblins = Squad.create_new(archetype=goblins_arch)

        orc_home_hex = HexCoordinates.from_axial(6, 0)
        orc_base_army = StrategicArmy(faction_id=orc_faction.id, current_hex=orc_home_hex)
        orc_base_army.add_squad(goblins)
        world.add_army(orc_base_army)

        # Отправляем караван на 2 такта добычи
        expedition = await expedition_service.dispatch_expedition(
            world_state=world,
            squad_id=goblins.id,
            faction_id=orc_faction.id,
            target_hex=target_mine_hex,
            home_hex=orc_home_hex,
            mining_duration_ticks=2,
        )
        caravan_army = world.get_army(expedition.expedition_army_id or "")
        assert caravan_army is not None

        # 4. Боевой легион Людей выдвигается в Ничью землю
        legion_squad = Squad.create_new(archetype=peasants_arch)
        legion_army = StrategicArmy(
            faction_id=human_faction.id,
            name="Передовой легион",
            current_hex=human_home_hex,
            target_hex=neutral_hex,
            planned_path=[
                HexCoordinates.from_axial(1, 0),
                HexCoordinates.from_axial(2, 0),
                neutral_hex,
            ],
            pace=StrategicMovementPace.MARCH,  # 2 гекса за такт
        )
        legion_army.add_squad(legion_squad)
        world.add_army(legion_army)

        # Вражеский патруль орков в Ничьей земле
        orc_patrol = StrategicArmy(
            faction_id=orc_faction.id,
            name="Орочий дозор",
            current_hex=neutral_hex,
            pace=StrategicMovementPace.CAUTIOUS,
        )
        world.add_army(orc_patrol)

        # =========================================================================
        # ТАКТ 1: Продвижение армий, старт добычи на ферме, марш каравана
        # =========================================================================

        report_t1 = await orchestrator.execute_turn(world)
        assert report_t1.events_report.ticks_elapsed == 1
        assert barracks.construction_ticks_remaining == 1
        # 300 (старт) + 80 (ферма) - 200 (содержание двух отрядов по 100 еды) = 180.0
        assert human_faction.resources[ResourceType.FOOD] == pytest.approx(180.0)
        assert legion_army.current_hex == HexCoordinates.from_axial(2, 0)

        # =========================================================================
        # ТАКТ 2: Завершение стройки казарм и боевое столкновение в Ничьей земле
        # =========================================================================

        report_t2 = await orchestrator.execute_turn(world)
        assert barracks.is_under_construction is False
        assert (
            "Казармы легиона"
            in report_t2.economy_reports[human_faction.id].completed_building_names
        )

        # Легион людей вступил на нейтральный гекс с орочьим дозором
        assert legion_army.current_hex == neutral_hex
        assert len(report_t2.movement_report.encounters) == 1
        encounter = report_t2.movement_report.encounters[0]
        assert encounter.hex_coordinates == neutral_hex
        assert encounter.faction_a_id == human_faction.id
        assert encounter.faction_b_id == orc_faction.id

        # =========================================================================
        # ТАКТ 3: Переход в Неоновые часы и 1-й такт активной добычи золота караваном
        # =========================================================================

        world.time.current_hour = 12  # Продвижение на 4 часа переведет в 16:00 (Неоновые часы)
        report_t3 = await orchestrator.execute_turn(world)

        assert report_t3.events_report.is_neon_hours is True
        assert report_t3.events_report.phase_changed is True

        # Караван орков ведет 1-й такт добычи
        assert expedition.status.value == "mining"
        assert expedition.accumulated_cargo[ResourceType.GOLD] == 225.0

        # =========================================================================
        # ТАКТ 4: 2-й такт добычи, завершение работ и марш каравана обратно на базу
        # =========================================================================

        report_t4 = await orchestrator.execute_turn(world)  # noqa: F841

        # Караван орков закончил добычу, развернулся и вернулся на базу
        assert expedition.status.value == "traveling_back"
        assert expedition.accumulated_cargo[ResourceType.GOLD] == 450.0
        assert caravan_army.current_hex == orc_home_hex

        # =========================================================================
        # ТАКТ 5: Разгрузка 450 золота в казну Орды, мародерство и деградация трофеев
        # =========================================================================

        loot_site = BattlefieldLootSite(
            hex_coordinates=neutral_hex,
            origin_battle_id="battle_epic_01",
            salvageable_equipment={"wpn_axe": 10},
            ticks_remaining=1,
        )
        world.add_battlefield_site(loot_site)

        orc_gold_before = orc_faction.resources[ResourceType.GOLD]
        report_t5 = await orchestrator.execute_turn(world)

        # Разгрузка каравана завершена
        assert expedition.id in report_t5.completed_expedition_ids
        assert expedition.status.value == "completed"
        assert orc_faction.resources[ResourceType.GOLD] == pytest.approx(
            orc_gold_before + 450.0
        )

        # Трофеи истлели за 1 такт и были удалены из реестра мира
        assert loot_site.id in report_t5.events_report.decayed_battlefield_ids
        assert world.get_battlefield_at(neutral_hex) is None
