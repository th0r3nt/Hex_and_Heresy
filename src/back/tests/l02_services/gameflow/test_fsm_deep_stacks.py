"""
Интеграционные тесты глубоких стеков состояний конечного автомата (FSM),
вложенных настроек, дипломатических аудиенций, экранов паузы и завершения игры.
"""

import pytest

from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.constants import GlobalEventCategory
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.gameflow.facade import GameFlowFacade
from src.back.l02_services.gameflow.fsm import GameFlowFSM
from src.back.l02_services.gameflow.guards import (
    ActionForbiddenInCurrentStateError,
    WorldStateNotBoundError,
)
from src.back.l02_services.gameflow.states import GameState


class FakeEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args, **kwargs) -> None:
        self.published.append((event_name, kwargs))


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def battle_state() -> TacticalBattleState:
    return TacticalBattleState()


class TestFSMDeepModalStacksAndTransitions:
    @pytest.mark.asyncio
    async def test_deep_nested_pause_and_settings_navigation(self, fake_bus, battle_state):
        fsm = GameFlowFSM(initial_state=GameState.MAIN_MENU, event_bus=fake_bus)
        facade = GameFlowFacade(fsm=fsm, event_bus=fake_bus)

        world = WorldState()
        facade.bind_world_state(world)

        # 1. Главное меню -> Старт партии -> Стратегическая карта
        await facade.start_new_game()
        assert facade.current_state == GameState.STRATEGIC_MAP

        # 2. Вход в тактический бой
        await facade.enter_tactical_combat(
            hex_coords=HexCoordinates.from_axial(1, 1),
            attacker_faction_id="humans",
            defender_faction_id="greenskins",
            battle_state=battle_state,
        )
        assert facade.current_state == GameState.TACTICAL_COMBAT

        # 3. Во время боя ставим на паузу (TACTICAL_COMBAT -> PAUSE)
        await facade.pause_game()
        assert facade.current_state == GameState.PAUSE

        # 4. Из паузы открываем настройки (PAUSE -> SETTINGS)
        await facade.open_settings()
        assert facade.current_state == GameState.SETTINGS

        # 5. Закрываем настройки -> возврат строго в PAUSE
        await facade.close_settings()
        assert facade.current_state == GameState.PAUSE

        # 6. Снимаем паузу -> возврат строго в TACTICAL_COMBAT
        await facade.resume_game()
        assert facade.current_state == GameState.TACTICAL_COMBAT

        # 7. Завершаем бой -> возврат на глобальную карту
        await facade.finish_tactical_combat(
            battle_id=battle_state.id, victor_faction_id="humans"
        )
        assert facade.current_state == GameState.STRATEGIC_MAP

    @pytest.mark.asyncio
    async def test_diplomatic_session_lifecycle(self, fake_bus):
        fsm = GameFlowFSM(initial_state=GameState.MAIN_MENU, event_bus=fake_bus)
        facade = GameFlowFacade(fsm=fsm, event_bus=fake_bus)
        facade.bind_world_state(WorldState())

        await facade.start_new_game()
        assert facade.current_state == GameState.STRATEGIC_MAP

        # Открываем аудиенцию у эльфийского лорда
        await facade.open_diplomatic_session(
            initiator_faction_id="humans",
            target_faction_id="elfs",
            ambassador_id="amb_01",
        )
        assert facade.current_state == GameState.DIPLOMATIC_SESSION

        # Во время дипломатии запрещено строить здания
        with pytest.raises(ActionForbiddenInCurrentStateError):
            facade.assert_can_build()

        # Закрываем переговоры
        await facade.close_diplomatic_session()
        assert facade.current_state == GameState.STRATEGIC_MAP
        facade.assert_can_build()

    @pytest.mark.asyncio
    async def test_global_event_modal_resolution(self, fake_bus):
        fsm = GameFlowFSM(initial_state=GameState.MAIN_MENU, event_bus=fake_bus)
        facade = GameFlowFacade(fsm=fsm, event_bus=fake_bus)
        facade.bind_world_state(WorldState())

        await facade.start_new_game()

        crisis_event = GlobalEvent(
            id="event_solar_flare",
            name="Неоновая буря",
            description="...",
            category=GlobalEventCategory.WEATHER,
        )

        await facade.show_global_event(crisis_event)
        assert facade.current_state == GameState.GLOBAL_EVENT_RESOLUTION

        await facade.resolve_global_event()
        assert facade.current_state == GameState.STRATEGIC_MAP

    @pytest.mark.asyncio
    async def test_game_over_clears_state_stack_on_quit_to_menu(self, fake_bus, battle_state):
        fsm = GameFlowFSM(initial_state=GameState.MAIN_MENU, event_bus=fake_bus)
        facade = GameFlowFacade(fsm=fsm, event_bus=fake_bus)
        world = WorldState()
        facade.bind_world_state(world)

        await facade.start_new_game()
        await facade.enter_tactical_combat(
            hex_coords=HexCoordinates.from_axial(0, 0),
            attacker_faction_id="humans",
            defender_faction_id="greenskins",
            battle_state=battle_state,
        )

        # Фиксируем гибель Цитадели и окончание игры
        await facade.trigger_game_over(
            is_player_victorious=False,
            reason="Цитадель Альт-Атласа пала под натиском орды.",
            total_ticks=85,
        )
        assert facade.current_state == GameState.GAME_OVER

        # Выход в главное меню полностью очищает стек истории
        await facade.quit_to_main_menu()
        assert facade.current_state == GameState.MAIN_MENU
        assert len(fsm._state_stack) == 0

    @pytest.mark.asyncio
    async def test_combat_without_bound_world_state_raises_error(self, battle_state):
        facade = GameFlowFacade()
        await facade.start_new_game()

        # WorldState не был привязан через bind_world_state
        with pytest.raises(WorldStateNotBoundError):
            await facade.enter_tactical_combat(
                hex_coords=HexCoordinates.from_axial(0, 0),
                attacker_faction_id="humans",
                defender_faction_id="greenskins",
                battle_state=battle_state,
            )
