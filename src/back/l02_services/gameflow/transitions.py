"""
Матрица переходов конечного автомата игры.
"""

from dataclasses import dataclass, field
from src.back.l02_services.gameflow.guards import (
    GuardFunction,
    guard_combat_payload_valid,
    guard_diplomacy_payload_valid,
    guard_game_over_payload_valid,
)
from src.back.l02_services.gameflow.states import GameFlowTrigger, GameState


@dataclass(frozen=True)
class TransitionRule:
    """Правило перехода между состояниями."""

    target_state: GameState
    guards: list[GuardFunction] = field(default_factory=list)
    saves_to_history: bool = (
        False  # сохранять ли предыдущее состояние в стек (для паузы/настроек)
    )


# ==================================================================
# МАТРИЦА ДОПУСТИМЫХ ПЕРЕХОДОВ
# ==================================================================

TRANSITION_MATRIX: dict[tuple[GameState, GameFlowTrigger], TransitionRule] = {
    # ====================================================
    # Из главного меню
    # ====================================================
    (GameState.MAIN_MENU, GameFlowTrigger.START_NEW_GAME): TransitionRule(
        target_state=GameState.STRATEGIC_MAP
    ),
    (GameState.MAIN_MENU, GameFlowTrigger.LOAD_SAVED_GAME): TransitionRule(
        target_state=GameState.STRATEGIC_MAP
    ),
    (GameState.MAIN_MENU, GameFlowTrigger.OPEN_SETTINGS): TransitionRule(
        target_state=GameState.SETTINGS,
        saves_to_history=True,
    ),
    # TODO: меню экрана разработчиков ("Авторы")?
    # ====================================================
    # Из режима глобальной карты
    # ====================================================
    (GameState.STRATEGIC_MAP, GameFlowTrigger.ENGAGE_COMBAT): TransitionRule(
        target_state=GameState.TACTICAL_COMBAT,
        guards=[guard_combat_payload_valid],
    ),
    (GameState.STRATEGIC_MAP, GameFlowTrigger.OPEN_AUDIENCE): TransitionRule(
        target_state=GameState.DIPLOMATIC_SESSION,
        guards=[guard_diplomacy_payload_valid],
    ),
    (GameState.STRATEGIC_MAP, GameFlowTrigger.TRIGGER_GLOBAL_EVENT): TransitionRule(
        target_state=GameState.GLOBAL_EVENT_RESOLUTION
    ),
    (GameState.STRATEGIC_MAP, GameFlowTrigger.PAUSE_GAME): TransitionRule(
        target_state=GameState.PAUSE,
        saves_to_history=True,
    ),
    (GameState.STRATEGIC_MAP, GameFlowTrigger.OPEN_SETTINGS): TransitionRule(
        target_state=GameState.SETTINGS,
        saves_to_history=True,
    ),
    (GameState.STRATEGIC_MAP, GameFlowTrigger.DECLARE_GAME_OVER): TransitionRule(
        target_state=GameState.GAME_OVER,
        guards=[guard_game_over_payload_valid],
    ),
    # ====================================================
    # Из тактического боя
    # ====================================================
    (GameState.TACTICAL_COMBAT, GameFlowTrigger.RESOLVE_COMBAT): TransitionRule(
        target_state=GameState.STRATEGIC_MAP
    ),
    (GameState.TACTICAL_COMBAT, GameFlowTrigger.PAUSE_GAME): TransitionRule(
        target_state=GameState.PAUSE,
        saves_to_history=True,
    ),
    (GameState.TACTICAL_COMBAT, GameFlowTrigger.OPEN_SETTINGS): TransitionRule(
        target_state=GameState.SETTINGS,
        saves_to_history=True,
    ),
    (GameState.TACTICAL_COMBAT, GameFlowTrigger.DECLARE_GAME_OVER): TransitionRule(
        target_state=GameState.GAME_OVER,
        guards=[guard_game_over_payload_valid],
    ),
    # ====================================================
    # Из дипломатической сессии
    # ====================================================
    (GameState.DIPLOMATIC_SESSION, GameFlowTrigger.CLOSE_AUDIENCE): TransitionRule(
        target_state=GameState.STRATEGIC_MAP
    ),
    (GameState.DIPLOMATIC_SESSION, GameFlowTrigger.PAUSE_GAME): TransitionRule(
        target_state=GameState.PAUSE,
        saves_to_history=True,
    ),
    # ====================================================
    # Из окна разрешения глобального события
    # ====================================================
    (GameState.GLOBAL_EVENT_RESOLUTION, GameFlowTrigger.RESOLVE_GLOBAL_EVENT): TransitionRule(
        target_state=GameState.STRATEGIC_MAP
    ),
    # ====================================================
    # Из паузы и настроек
    # ====================================================
    (GameState.PAUSE, GameFlowTrigger.RESUME_GAME): TransitionRule(
        target_state=GameState.STRATEGIC_MAP  # переопределяется возвратом из стека в FSM
    ),
    (GameState.PAUSE, GameFlowTrigger.OPEN_SETTINGS): TransitionRule(
        target_state=GameState.SETTINGS,
        saves_to_history=True,
    ),
    (GameState.PAUSE, GameFlowTrigger.QUIT_TO_MAIN_MENU): TransitionRule(
        target_state=GameState.MAIN_MENU
    ),
    (GameState.SETTINGS, GameFlowTrigger.CLOSE_SETTINGS): TransitionRule(
        target_state=GameState.MAIN_MENU  # переопределяется возвратом из стека в FSM
    ),
    # ====================================================
    # Из экрана окончания игры
    # ====================================================
    (GameState.GAME_OVER, GameFlowTrigger.QUIT_TO_MAIN_MENU): TransitionRule(
        target_state=GameState.MAIN_MENU
    ),
}
