"""
Тесты интеграции тактического конвейера ходов в TurnsFacade.
"""

import pytest

from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.combat.constants import BattleMapSize
from src.back.l01_domain.combat.models.state import TacticalBattleState, TacticalCellState
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions import NoArmiesLockedForBattleError
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.facade import TurnsFacade


def _build_battle_state() -> TacticalBattleState:
    state = TacticalBattleState(map_size=BattleMapSize.SMALL)
    for x in range(14):
        for y in range(14):
            state.cells.append(TacticalCellState(coordinates=CellCoordinates(x=x, y=y)))
    return state


def _place(battle_state: TacticalBattleState, squad_id: str, x: int, y: int) -> None:
    for cell in battle_state.cells:
        if cell.coordinates.x == x and cell.coordinates.y == y:
            cell.occupant_squad_id = squad_id
            break


def _make_archetype(race: FactionRace, faction_id: str) -> UnitArchetype:
    return UnitArchetype(
        id=f"unit_{faction_id}",
        race=race,
        faction_id=faction_id,
        name="Тестовый отряд",
        tier=1,
        default_unit_count=100,
        base_stats=BaseUnitStats(
            max_hp=20.0,
            base_speed=2.0,
            base_morale=50.0,
            size_category=UnitSizeCategory.MEDIUM,
        ),
    )


@pytest.fixture
def battle_hex() -> HexCoordinates:
    return HexCoordinates.from_axial(2, -1)


@pytest.fixture
def world_with_locked_battle(battle_hex):
    world = WorldState()

    attacker_squad = Squad.create_new(archetype=_make_archetype(FactionRace.HUMANS, "humans"))
    attacker_squad.id = "squad_attacker"
    attacker_army = StrategicArmy(
        id="army_attacker", faction_id="humans", current_hex=battle_hex
    )
    attacker_army.add_squad(attacker_squad)

    defender_squad = Squad.create_new(
        archetype=_make_archetype(FactionRace.GREENSKINS, "greenskins")
    )
    defender_squad.id = "squad_defender"
    defender_army = StrategicArmy(
        id="army_defender", faction_id="greenskins", current_hex=battle_hex
    )
    defender_army.add_squad(defender_squad)

    world.add_army(attacker_army)
    world.add_army(defender_army)

    battle_state = _build_battle_state()
    battle_state.attacker_squad_ids = ["squad_attacker"]
    battle_state.defender_squad_ids = ["squad_defender"]
    _place(battle_state, "squad_attacker", 1, 1)
    _place(battle_state, "squad_defender", 2, 1)

    world.lock_armies_for_battle(battle_state.id, ["army_attacker", "army_defender"])

    return world, battle_state, attacker_army, defender_army


class TestTurnsFacadeTacticalIntegration:
    @pytest.mark.asyncio
    async def test_execute_tactical_turn_uses_same_squad_references_from_armies(
        self, world_with_locked_battle
    ):
        world, battle_state, attacker_army, defender_army = world_with_locked_battle
        facade = TurnsFacade()

        assert attacker_army.is_in_tactical_battle is True
        assert defender_army.is_in_tactical_battle is True

        report = await facade.execute_tactical_turn(
            world_state=world, battle_state=battle_state
        )

        assert report.battle_id == battle_state.id
        assert report.tick == 1

        # Урон, нанесённый через фасад, обязан отразиться на исходном объекте
        # StrategicArmy.squads - фасад должен передавать оркестратору те же
        # самые ссылки на Squad, а не копии.
        defender_army.squads[0].state.unit_count = 42
        assert world.get_army("army_defender").squads[0].state.unit_count == 42

    @pytest.mark.asyncio
    async def test_execute_tactical_turn_releases_armies_and_registers_loot_on_finish(
        self, world_with_locked_battle
    ):
        world, battle_state, attacker_army, defender_army = world_with_locked_battle
        facade = TurnsFacade()

        # Защитник уже уничтожен - раунд должен зафиксировать исход боя.
        defender_army.squads[0].state.unit_count = 0

        report = await facade.execute_tactical_turn(
            world_state=world, battle_state=battle_state
        )

        assert report.is_battle_finished is True
        assert report.victor_faction_id == "humans"
        assert report.loot_site is not None

        assert battle_state.id not in world.active_battle_armies
        assert attacker_army.is_in_tactical_battle is False
        assert defender_army.is_in_tactical_battle is False
        assert report.loot_site.id in world.battlefield_sites

    @pytest.mark.asyncio
    async def test_execute_tactical_turn_raises_when_no_armies_locked(self, battle_hex):
        world = WorldState()
        battle_state = _build_battle_state()
        facade = TurnsFacade()

        with pytest.raises(NoArmiesLockedForBattleError):
            await facade.execute_tactical_turn(world_state=world, battle_state=battle_state)
