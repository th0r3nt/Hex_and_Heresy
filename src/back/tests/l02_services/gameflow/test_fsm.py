"""
Тесты для конечного автомата gameflow (FSM, guards, facade).
"""

import pytest

from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.maps.models.global_map import HexCoordinates
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
        assert new_state == GameState.GLOBAL_MAP
        assert fsm.current_state == GameState.GLOBAL_MAP

    @pytest.mark.asyncio
    async def test_invalid_transition_raises_error(self, fsm):
        # Нельзя начать тактический бой прямо из главного меню
        with pytest.raises(InvalidStateTransitionError):
            await fsm.trigger(GameFlowTrigger.ENGAGE_COMBAT)

    @pytest.mark.asyncio
    async def test_combat_guard_blocks_same_factions(self, fsm, dummy_battle_state):
        await fsm.trigger(GameFlowTrigger.START_NEW_GAME)

        invalid_payload = CombatTransitionPayload(
            hex_coordinates=HexCoordinates.from_axial(0, 0),
            attacker_faction_id="humans",
            defender_faction_id="humans",  # одна и та же фракция
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
        assert resolved_state == GameState.GLOBAL_MAP

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

        # Ставим на паузу из боя
        await fsm.trigger(GameFlowTrigger.PAUSE_GAME)
        assert fsm.current_state == GameState.PAUSE

        # Снимаем с паузы — должны вернуться именно в бой
        await fsm.trigger(GameFlowTrigger.RESUME_GAME)
        assert fsm.current_state == GameState.TACTICAL_COMBAT

    @pytest.mark.asyncio
    async def test_event_bus_notified_on_transition(self):
        bus = FakeEventBus()
        fsm_with_bus = GameFlowFSM(initial_state=GameState.MAIN_MENU, event_bus=bus)

        await fsm_with_bus.trigger(GameFlowTrigger.START_NEW_GAME)

        assert len(bus.published_events) == 1
        event_name, kwargs = bus.published_events[0]
        assert event_name == "gameflow.state_changed"
        assert kwargs["from_state"] == GameState.MAIN_MENU
        assert kwargs["to_state"] == GameState.GLOBAL_MAP


class TestGameFlowFacade:
    @pytest.mark.asyncio
    async def test_facade_gameplay_lifecycle(self, facade, dummy_battle_state):
        assert facade.current_state == GameState.MAIN_MENU

        # Старт игры
        await facade.start_new_game()
        assert facade.current_state == GameState.GLOBAL_MAP

        # На глобальной карте разрешено строительство и дипломатия
        facade.assert_can_build()
        facade.assert_can_perform_diplomacy()
        facade.assert_can_recruit()
        facade.assert_can_save()

        # Вход в бой
        await facade.enter_tactical_combat(
            hex_coords=HexCoordinates.from_axial(1, 0),
            attacker_faction_id="humans",
            defender_faction_id="greenskins",
            battle_state=dummy_battle_state,
        )
        assert facade.current_state == GameState.TACTICAL_COMBAT

        # В бою дипломатия и стройка блокируются
        with pytest.raises(ActionForbiddenInCurrentStateError):
            facade.assert_can_build()

        with pytest.raises(ActionForbiddenInCurrentStateError):
            facade.assert_can_perform_diplomacy()

        with pytest.raises(ActionForbiddenInCurrentStateError):
            facade.assert_can_save()

        # Завершение боя
        await facade.finish_tactical_combat(battle_id="b_1", victor_faction_id="humans")
        assert facade.current_state == GameState.GLOBAL_MAP

        # Конец игры
        await facade.trigger_game_over(
            is_player_victorious=True, reason="Цитадель врага пала", total_ticks=42
        )
        assert facade.current_state == GameState.GAME_OVER

        # Возврат в меню
        await facade.quit_to_main_menu()
        assert facade.current_state == GameState.MAIN_MENU
