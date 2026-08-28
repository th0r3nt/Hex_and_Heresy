"""
Гарнизоны в связке с остальными механиками такта: содержание в бюджете
фракции, налоговые настроения за стенами и оборона гекса базы.
"""

import pytest

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.combat.models.reports import (
    MoraleAndEnvironmentReport,
    TacticalTurnReport,
)
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import (
    GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO,
    ResourceType,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.garrison import Garrison
from src.back.l01_domain.maps.models.strategic import HexCoordinates, hex_zone_id
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.gameflow.facade import GameFlowFacade
from src.back.l02_services.gameflow.fsm import GameFlowFSM
from src.back.l02_services.gameflow.states import GameState
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.l02_services.turns.strategic.economy import StrategicEconomyService

CAPITAL_HEX = HexCoordinates.from_axial(4, -8)
CAPITAL_ZONE = hex_zone_id(CAPITAL_HEX)


# ==================================================================
# ВСПОМОГАТЕЛЬНОЕ
# ==================================================================


def _squad(unit_count: int = 100, upkeep_food: float = 1.0, upkeep_gold: float = 1.0) -> Squad:
    return Squad.create_new(
        archetype=UnitArchetype(
            id="unit_test_line",
            race=FactionRace.HUMANS,
            faction_id="humans",
            name="Городская стража",
            tier=1,
            default_unit_count=unit_count,
            base_stats=BaseUnitStats(max_hp=20.0),
            base_upkeep_food=upkeep_food,
            base_upkeep_gold=upkeep_gold,
        )
    )


class SpyTacticalOrchestrator:
    """
    Подставной оркестратор боя: запоминает, кого фасад вывел на поле.
    Сам расчет раунда здесь не важен - важен состав защитников.
    """

    def __init__(self) -> None:
        self.received_squad_ids: set[str] = set()

    async def execute_turn(self, battle_state, squads, strategic_hex, **_) -> TacticalTurnReport:
        self.received_squad_ids = set(squads)
        return TacticalTurnReport(
            battle_id=battle_state.id,
            tick=battle_state.current_tick,
            phase=battle_state.phase,
            morale_report=MoraleAndEnvironmentReport(),
        )


def _world_with_garrison(faction: Faction) -> tuple[WorldState, Garrison]:
    """Мир, где у фракции есть цитадель с готовым гарнизоном."""
    faction.capital_hex = CAPITAL_HEX

    world_state = WorldState()
    world_state.add_faction(faction)

    garrison = Garrison(
        zone_id=CAPITAL_ZONE,
        faction_id=faction.id,
        hex_coordinates=CAPITAL_HEX,
    )
    world_state.add_garrison(garrison)
    return world_state, garrison


# ==================================================================
# ЭКОНОМИКА: СОДЕРЖАНИЕ ГАРНИЗОНОВ
# ==================================================================


class TestGarrisonUpkeep:
    @pytest.mark.asyncio
    async def test_garrison_food_is_charged_with_the_discount(
        self, human_faction, fake_bus
    ):
        """
        Отряд за стенами ест на GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO меньше,
        чем тот же отряд в поле.
        """
        world_state, garrison = _world_with_garrison(human_faction)
        squad = _squad(unit_count=100, upkeep_food=1.0)
        garrison.station_squad(squad)

        human_faction.resources[ResourceType.FOOD] = 1000.0
        human_faction.resources[ResourceType.GOLD] = 1000.0

        service = StrategicEconomyService(event_bus=fake_bus)
        report = (await service.process_factions_economy(world_state))[human_faction.id]

        expected_food = squad.upkeep_food * (1.0 - GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO)
        assert report.garrison_upkeep_food == pytest.approx(expected_food)
        assert report.upkeep_food_required == pytest.approx(expected_food)
        assert report.garrison_upkeep_food < squad.upkeep_food

    @pytest.mark.asyncio
    async def test_garrison_gold_is_charged_in_full(self, human_faction, fake_bus):
        """Жалование гарнизона идет в казну без скидок."""
        world_state, garrison = _world_with_garrison(human_faction)
        squad = _squad(unit_count=100, upkeep_gold=1.0)
        garrison.station_squad(squad)

        human_faction.resources[ResourceType.FOOD] = 1000.0
        human_faction.resources[ResourceType.GOLD] = 1000.0

        service = StrategicEconomyService(event_bus=fake_bus)
        report = (await service.process_factions_economy(world_state))[human_faction.id]

        assert report.garrison_upkeep_gold == pytest.approx(squad.upkeep_gold)

    @pytest.mark.asyncio
    async def test_garrison_and_field_army_share_one_budget(
        self, human_faction, sample_army, fake_bus
    ):
        """Смета такта складывает содержание армий и гарнизонов."""
        world_state, garrison = _world_with_garrison(human_faction)
        world_state.add_army(sample_army)
        garrison.station_squad(_squad())

        human_faction.resources[ResourceType.FOOD] = 5000.0
        human_faction.resources[ResourceType.GOLD] = 5000.0

        service = StrategicEconomyService(event_bus=fake_bus)
        report = (await service.process_factions_economy(world_state))[human_faction.id]

        assert report.upkeep_food_required == pytest.approx(
            sample_army.total_upkeep_food + garrison.total_upkeep_food
        )
        assert report.upkeep_gold_required == pytest.approx(
            sample_army.total_upkeep_gold + garrison.total_upkeep_gold
        )

    @pytest.mark.asyncio
    async def test_predatory_taxes_hit_the_garrison_morale(self, human_faction, fake_bus):
        """Грабительские сборы портят настроение и за стенами тоже."""
        world_state, garrison = _world_with_garrison(human_faction)
        squad = _squad()
        garrison.station_squad(squad)
        morale_before = squad.state.morale

        human_faction.set_tax_rate(2.0)
        human_faction.resources[ResourceType.FOOD] = 1000.0
        human_faction.resources[ResourceType.GOLD] = 1000.0

        service = StrategicEconomyService(event_bus=fake_bus)
        await service.process_factions_economy(world_state)

        assert squad.state.morale < morale_before


# ==================================================================
# ОБОРОНА ГЕКСА БАЗЫ
# ==================================================================


class TestGarrisonDefendsItsLand:
    @pytest.mark.asyncio
    async def test_battle_on_the_base_hex_draws_in_the_garrison(
        self, human_faction, fake_bus
    ):
        """
        Штурм цитадели поднимает весь гарнизон: и ополчение, и оставленные
        игроком войска дерутся вместе с мобильной армией.
        """
        world_state, garrison = _world_with_garrison(human_faction)
        garrison.sync_militia_capacity(level=1, recruit=_squad)
        stationed = _squad()
        garrison.station_squad(stationed)

        defender_army = StrategicArmy(
            faction_id=human_faction.id, name="Гвардия", current_hex=CAPITAL_HEX
        )
        defender_army.add_squad(_squad())
        world_state.add_army(defender_army)

        battle_state = TacticalBattleState(
            attacker_faction_id="greenskins",
            defender_faction_id=human_faction.id,
        )
        world_state.lock_armies_for_battle(battle_state.id, [defender_army.id])

        spy = SpyTacticalOrchestrator()
        facade = TurnsFacade(tactical_orchestrator=spy, event_bus=fake_bus)
        await facade.execute_tactical_turn(
            world_state=world_state, battle_state=battle_state
        )

        assert stationed.id in spy.received_squad_ids
        for militia in garrison.militia_squads:
            assert militia.id in spy.received_squad_ids
        # Мобильная армия защитника при этом никуда не делась
        assert defender_army.squads[0].id in spy.received_squad_ids

    @pytest.mark.asyncio
    async def test_assault_freezes_and_then_releases_the_garrison(self, human_faction):
        """
        Пока идет штурм, состав гарнизона заморожен; после боя лок снимается.
        """
        world_state, garrison = _world_with_garrison(human_faction)
        gameflow = GameFlowFacade(fsm=GameFlowFSM(initial_state=GameState.STRATEGIC_MAP))
        gameflow.bind_world_state(world_state)

        battle_state = TacticalBattleState(
            attacker_faction_id="greenskins",
            defender_faction_id=human_faction.id,
        )
        await gameflow.enter_tactical_combat(
            hex_coords=CAPITAL_HEX,
            attacker_faction_id="greenskins",
            defender_faction_id=human_faction.id,
            battle_state=battle_state,
        )

        assert garrison.is_locked_in_battle is True

        await gameflow.finish_tactical_combat(
            battle_id=battle_state.id, victor_faction_id=human_faction.id
        )

        assert garrison.is_locked_in_battle is False
