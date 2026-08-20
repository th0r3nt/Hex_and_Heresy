"""
Тесты для конечного автомата gameflow (FSM, guards, facade).
"""

import pytest

from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.gameflow.facade import GameFlowFacade
from src.back.l02_services.gameflow.fsm import GameFlowFSM
from src.back.l02_services.gameflow.guards import (
    ActionForbiddenInCurrentStateError,
    GuardConditionFailedError,
    InvalidStateTransitionError,
)
from src.back.l02_services.gameflow.states import (
    CombatTransitionPayload,
    GameFlowTrigger,
    GameState,
)
from src.back.utils.event.registry import GameEvents


class FakeEventBus:
    def __init__(self) -> None:
        self.published_events: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args, **kwargs) -> None:
        self.published_events.append((event_name, kwargs))


@pytest.fixture
def dummy_battle_state() -> TacticalBattleState:
    return TacticalBattleState()


@pytest.fixture
def fsm() -> GameFlowFSM:
    return GameFlowFSM(initial_state=GameState.MAIN_MENU)


@pytest.fixture
def facade(fsm) -> GameFlowFacade:
    return GameFlowFacade(fsm=fsm)


class TestGameFlowFSM:
    @pytest.mark.asyncio
    async def test_initial_state(self, fsm):
        assert fsm.current_state == GameState.MAIN_MENU

    @pytest.mark.asyncio
    async def test_start_new_game_transition(self, fsm):
        new_state = await fsm.trigger(GameFlowTrigger.START_NEW_GAME)
        assert new_state == GameState.STRATEGIC_MAP
        assert fsm.current_state == GameState.STRATEGIC_MAP

    @pytest.mark.asyncio
    async def test_invalid_transition_raises_error(self, fsm):
        with pytest.raises(InvalidStateTransitionError):
            await fsm.trigger(GameFlowTrigger.ENGAGE_COMBAT)

    @pytest.mark.asyncio
    async def test_combat_guard_blocks_same_factions(self, fsm, dummy_battle_state):
        await fsm.trigger(GameFlowTrigger.START_NEW_GAME)

        invalid_payload = CombatTransitionPayload(
            hex_coordinates=HexCoordinates.from_axial(0, 0),
            attacker_faction_id="humans",
            defender_faction_id="humans",
            battle_state=dummy_battle_state,
        )

        with pytest.raises(GuardConditionFailedError):
            await fsm.trigger(GameFlowTrigger.ENGAGE_COMBAT, payload=invalid_payload)

    @pytest.mark.asyncio
    async def test_valid_combat_transition_and_resolution(self, fsm, dummy_battle_state):
        await fsm.trigger(GameFlowTrigger.START_NEW_GAME)

        valid_payload = CombatTransitionPayload(
            hex_coordinates=HexCoordinates.from_axial(0, 0),
            attacker_faction_id="humans",
            defender_faction_id="orcs",
            battle_state=dummy_battle_state,
        )

        combat_state = await fsm.trigger(GameFlowTrigger.ENGAGE_COMBAT, payload=valid_payload)
        assert combat_state == GameState.TACTICAL_COMBAT

        resolved_state = await fsm.trigger(GameFlowTrigger.RESOLVE_COMBAT)
        assert resolved_state == GameState.STRATEGIC_MAP

    @pytest.mark.asyncio
    async def test_pause_and_resume_preserves_previous_state(self, fsm, dummy_battle_state):
        await fsm.trigger(GameFlowTrigger.START_NEW_GAME)

        valid_payload = CombatTransitionPayload(
            hex_coordinates=HexCoordinates.from_axial(0, 0),
            attacker_faction_id="humans",
            defender_faction_id="orcs",
            battle_state=dummy_battle_state,
        )
        await fsm.trigger(GameFlowTrigger.ENGAGE_COMBAT, payload=valid_payload)
        assert fsm.current_state == GameState.TACTICAL_COMBAT

        await fsm.trigger(GameFlowTrigger.PAUSE_GAME)
        assert fsm.current_state == GameState.PAUSE

        await fsm.trigger(GameFlowTrigger.RESUME_GAME)
        assert fsm.current_state == GameState.TACTICAL_COMBAT

    @pytest.mark.asyncio
    async def test_event_bus_notified_on_transition(self):
        bus = FakeEventBus()
        fsm_with_bus = GameFlowFSM(initial_state=GameState.MAIN_MENU, event_bus=bus)

        await fsm_with_bus.trigger(GameFlowTrigger.START_NEW_GAME)

        assert len(bus.published_events) == 1
        event_name, kwargs = bus.published_events[0]
        assert event_name == GameEvents.GameFlow.STATE_CHANGED
        assert kwargs["from_state"] == GameState.MAIN_MENU
        assert kwargs["to_state"] == GameState.STRATEGIC_MAP


class TestGameFlowFacade:
    @pytest.mark.asyncio
    async def test_facade_gameplay_lifecycle(self, facade, dummy_battle_state):
        assert facade.current_state == GameState.MAIN_MENU

        await facade.start_new_game()
        assert facade.current_state == GameState.STRATEGIC_MAP

        world = WorldState()
        facade.bind_world_state(world)

        facade.assert_can_build()
        facade.assert_can_perform_diplomacy()
        facade.assert_can_recruit()
        facade.assert_can_save()

        await facade.enter_tactical_combat(
            hex_coords=HexCoordinates.from_axial(1, 0),
            attacker_faction_id="humans",
            defender_faction_id="greenskins",
            battle_state=dummy_battle_state,
        )
        assert facade.current_state == GameState.TACTICAL_COMBAT

        with pytest.raises(ActionForbiddenInCurrentStateError):
            facade.assert_can_build()

        with pytest.raises(ActionForbiddenInCurrentStateError):
            facade.assert_can_perform_diplomacy()

        with pytest.raises(ActionForbiddenInCurrentStateError):
            facade.assert_can_save()

        await facade.finish_tactical_combat(battle_id="b_1", victor_faction_id="humans")
        assert facade.current_state == GameState.STRATEGIC_MAP

        await facade.trigger_game_over(
            is_player_victorious=True, reason="Цитадель врага пала", total_ticks=42
        )
        assert facade.current_state == GameState.GAME_OVER

        await facade.quit_to_main_menu()
        assert facade.current_state == GameState.MAIN_MENU
