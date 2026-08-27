"""
Тесты налогового этапа глобального такта: сбор золота с административных
центров, настроения гарнизонов, забастовки рабочих и бунты в союзных землях.
"""

from random import Random

import pytest

from src.back.l01_domain.factions.constants import (
    BASE_TAX_HQ_PER_LEVEL,
    BASE_TAX_ZONE_PER_LEVEL,
    ResourceType,
    WorkerAssignmentStatus,
)
from src.back.l01_domain.factions.models.buildings import RegionalHall
from src.back.l01_domain.factions.models.workers import WorkerAssignment
from src.back.l01_domain.maps.constants import ALLIED_LANDS_RING_RADIUS
from src.back.l01_domain.maps.models.strategic import HexCoordinates, hex_distance
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.economy import StrategicEconomyService
from src.back.utils.event.registry import GameEvents


class AlwaysRolls(Random):
    """Кости с заранее известным исходом: 0.0 - событие случилось, 1.0 - нет."""

    def __init__(self, value: float) -> None:
        super().__init__()
        self._value = value

    def random(self) -> float:
        return self._value


def _working_assignment(world: WorldState, faction_id: str, squad_id: str) -> WorkerAssignment:
    assignment = WorkerAssignment.create_stationary(
        squad_id=squad_id,
        faction_id=faction_id,
        building_id="b_mine",
        needs_warmup=False,
    )
    world.add_worker_assignment(assignment)
    return assignment


# ==================================================================
# СБОР НАЛОГОВ
# ==================================================================


class TestTaxCollection:
    @pytest.mark.asyncio
    async def test_citadel_and_halls_fill_the_treasury(self, human_faction, fake_bus):
        human_faction.resources[ResourceType.GOLD] = 0.0
        human_faction.gain_zone("zone_01")
        human_faction.add_regional_hall(
            RegionalHall(faction_id=human_faction.id, zone_id="zone_01", name="Ратуша")
        )

        world = WorldState()
        world.add_faction(human_faction)

        service = StrategicEconomyService(event_bus=fake_bus)
        reports = await service.process_factions_economy(world)

        expected = BASE_TAX_HQ_PER_LEVEL + BASE_TAX_ZONE_PER_LEVEL
        report = reports[human_faction.id]
        assert report.tax_income_gold == pytest.approx(expected)
        assert report.income_gold == pytest.approx(expected)
        assert human_faction.resources[ResourceType.GOLD] == pytest.approx(expected)

        event_names = [name for name, _ in fake_bus.events]
        assert GameEvents.Economy.TAXES_COLLECTED in event_names

    @pytest.mark.asyncio
    async def test_slider_scales_the_collected_gold(self, human_faction, fake_bus):
        human_faction.resources[ResourceType.GOLD] = 0.0
        human_faction.set_tax_rate(1.5)

        world = WorldState()
        world.add_faction(human_faction)

        reports = await StrategicEconomyService(event_bus=fake_bus).process_factions_economy(
            world
        )

        assert reports[human_faction.id].tax_income_gold == pytest.approx(
            BASE_TAX_HQ_PER_LEVEL * 1.5
        )

    @pytest.mark.asyncio
    async def test_tax_holiday_collects_nothing(self, human_faction, fake_bus):
        human_faction.resources[ResourceType.GOLD] = 0.0
        human_faction.set_tax_rate(0.0)

        world = WorldState()
        world.add_faction(human_faction)

        reports = await StrategicEconomyService(event_bus=fake_bus).process_factions_economy(
            world
        )

        assert reports[human_faction.id].tax_income_gold == 0.0
        assert human_faction.resources[ResourceType.GOLD] == 0.0

        event_names = [name for name, _ in fake_bus.events]
        assert GameEvents.Economy.TAXES_COLLECTED not in event_names


# ==================================================================
# НАСТРОЕНИЯ ГАРНИЗОНОВ
# ==================================================================


class TestGarrisonMood:
    @pytest.mark.asyncio
    async def test_tax_holiday_lifts_garrison_morale(
        self, human_faction, sample_army, fake_bus
    ):
        human_faction.set_tax_rate(0.0)
        squad = sample_army.squads[0]
        squad.apply_morale_shock(20.0)
        morale_before = squad.state.morale

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(sample_army)

        reports = await StrategicEconomyService(event_bus=fake_bus).process_factions_economy(
            world
        )

        assert reports[human_faction.id].tax_morale_delta == pytest.approx(5.0)
        assert squad.state.morale == pytest.approx(morale_before + 5.0)

    @pytest.mark.asyncio
    async def test_predatory_taxes_break_garrison_morale(
        self, human_faction, sample_army, fake_bus
    ):
        human_faction.set_tax_rate(2.0)
        squad = sample_army.squads[0]
        morale_before = squad.state.morale

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(sample_army)

        reports = await StrategicEconomyService(
            event_bus=fake_bus, rng=AlwaysRolls(1.0)
        ).process_factions_economy(world)

        assert reports[human_faction.id].tax_morale_delta == pytest.approx(-20.0)
        assert squad.state.morale == pytest.approx(morale_before - 20.0)

    @pytest.mark.asyncio
    async def test_baseline_rate_does_not_touch_morale(
        self, human_faction, sample_army, fake_bus
    ):
        squad = sample_army.squads[0]
        morale_before = squad.state.morale

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(sample_army)

        reports = await StrategicEconomyService(event_bus=fake_bus).process_factions_economy(
            world
        )

        assert reports[human_faction.id].tax_morale_delta == 0.0
        assert squad.state.morale == pytest.approx(morale_before)


# ==================================================================
# ЗАБАСТОВКИ РАБОЧИХ
# ==================================================================


class TestWorkerStrikes:
    @pytest.mark.asyncio
    async def test_raised_taxes_send_workers_on_strike(self, human_faction, fake_bus):
        human_faction.set_tax_rate(1.2)

        world = WorldState()
        world.add_faction(human_faction)
        assignment = _working_assignment(world, human_faction.id, "squad_workers")

        reports = await StrategicEconomyService(
            event_bus=fake_bus, rng=AlwaysRolls(0.0)
        ).process_factions_economy(world)

        assert reports[human_faction.id].striking_worker_squad_ids == ["squad_workers"]
        assert assignment.status == WorkerAssignmentStatus.WARMING_UP
        assert assignment.warmup_ticks_remaining == 1

        event_names = [name for name, _ in fake_bus.events]
        assert GameEvents.Economy.WORKERS_ON_STRIKE in event_names

    @pytest.mark.asyncio
    async def test_strike_costs_the_faction_the_next_tick_of_mining(
        self, human_faction, fake_bus
    ):
        """Бастующий разогревается заново, поэтому простой длится целый такт."""
        human_faction.set_tax_rate(1.2)

        world = WorldState()
        world.add_faction(human_faction)
        assignment = _working_assignment(world, human_faction.id, "squad_workers")

        service = StrategicEconomyService(event_bus=fake_bus, rng=AlwaysRolls(0.0))
        await service.process_factions_economy(world)
        assert assignment.status == WorkerAssignmentStatus.WARMING_UP

        # Следующий такт: разогрев закончился, но новая проверка снова роняет отряд
        await service.process_factions_economy(world)
        assert assignment.status == WorkerAssignmentStatus.WARMING_UP

    @pytest.mark.asyncio
    async def test_lucky_roll_keeps_workers_at_the_bench(self, human_faction, fake_bus):
        human_faction.set_tax_rate(1.4)

        world = WorldState()
        world.add_faction(human_faction)
        assignment = _working_assignment(world, human_faction.id, "squad_workers")

        reports = await StrategicEconomyService(
            event_bus=fake_bus, rng=AlwaysRolls(1.0)
        ).process_factions_economy(world)

        assert reports[human_faction.id].striking_worker_squad_ids == []
        assert assignment.status == WorkerAssignmentStatus.WORKING

    @pytest.mark.asyncio
    async def test_fair_taxes_never_stop_production(self, human_faction, fake_bus):
        world = WorldState()
        world.add_faction(human_faction)
        assignment = _working_assignment(world, human_faction.id, "squad_workers")

        reports = await StrategicEconomyService(
            event_bus=fake_bus, rng=AlwaysRolls(0.0)
        ).process_factions_economy(world)

        assert reports[human_faction.id].striking_worker_squad_ids == []
        assert assignment.status == WorkerAssignmentStatus.WORKING


# ==================================================================
# БУНТЫ В СОЮЗНЫХ ЗЕМЛЯХ
# ==================================================================


class TestTaxRiots:
    @pytest.mark.asyncio
    async def test_predatory_taxes_raise_a_mob_on_allied_lands(self, human_faction, fake_bus):
        human_faction.set_tax_rate(2.0)
        capital = HexCoordinates.from_axial(0, 0)
        human_faction.capital_hex = capital

        world = WorldState()
        world.add_faction(human_faction)

        reports = await StrategicEconomyService(
            event_bus=fake_bus, rng=AlwaysRolls(0.0)
        ).process_factions_economy(world)

        riot_army_id = reports[human_faction.id].riot_army_id
        assert riot_army_id is not None

        riot_army = world.get_army(riot_army_id)
        assert riot_army is not None
        assert riot_army.faction_id == "neutrals"
        assert riot_army.squads, "бунт без бунтовщиков"
        assert hex_distance(riot_army.current_hex, capital) == ALLIED_LANDS_RING_RADIUS

        event_names = [name for name, _ in fake_bus.events]
        assert GameEvents.Economy.TAX_RIOT_ERUPTED in event_names

    @pytest.mark.asyncio
    async def test_raised_but_not_predatory_taxes_do_not_riot(self, human_faction, fake_bus):
        human_faction.set_tax_rate(1.4)
        human_faction.capital_hex = HexCoordinates.from_axial(0, 0)

        world = WorldState()
        world.add_faction(human_faction)

        reports = await StrategicEconomyService(
            event_bus=fake_bus, rng=AlwaysRolls(0.0)
        ).process_factions_economy(world)

        assert reports[human_faction.id].riot_army_id is None
        assert world.armies == {}

    @pytest.mark.asyncio
    async def test_faction_without_capital_has_nowhere_to_riot(self, human_faction, fake_bus):
        human_faction.set_tax_rate(2.0)
        human_faction.capital_hex = None

        world = WorldState()
        world.add_faction(human_faction)

        reports = await StrategicEconomyService(
            event_bus=fake_bus, rng=AlwaysRolls(0.0)
        ).process_factions_economy(world)

        assert reports[human_faction.id].riot_army_id is None
        assert world.armies == {}

    @pytest.mark.asyncio
    async def test_calm_roll_leaves_the_peasants_at_home(self, human_faction, fake_bus):
        human_faction.set_tax_rate(2.0)
        human_faction.capital_hex = HexCoordinates.from_axial(0, 0)

        world = WorldState()
        world.add_faction(human_faction)

        reports = await StrategicEconomyService(
            event_bus=fake_bus, rng=AlwaysRolls(1.0)
        ).process_factions_economy(world)

        assert reports[human_faction.id].riot_army_id is None
