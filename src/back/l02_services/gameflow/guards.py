"""
Стражи и предикаты допустимости действий в текущем режиме игры.
"""

from typing import Any, Callable, Optional

from src.back.l01_domain.exceptions.base import DomainError
from src.back.l01_domain.world.models.gameflow import (
    CombatTransitionPayload,
    DiplomacyTransitionPayload,
    GameOverPayload,
)
from src.back.l02_services.gameflow.states import GameFlowTrigger, GameState


class GameFlowError(DomainError):
    """
    Базовое исключение для ошибок управления игровым потоком.
    """


class InvalidStateTransitionError(GameFlowError):
    """
    Попытка совершить недопустимый переход в конечном автомате.
    """

    def __init__(self, from_state: GameState, trigger: GameFlowTrigger) -> None:
        self.from_state = from_state
        self.trigger = trigger
        super().__init__(
            f"Недопустимый переход из состояния '{from_state.value}' по триггеру '{trigger.value}'."
        )


class GuardConditionFailedError(GameFlowError):
    """
    Отказ перехода из-за невыполнения условий стража.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Переход заблокирован стражем: {reason}.")


class ActionForbiddenInCurrentStateError(GameFlowError):
    """
    Попытка выполнить игровое действие, запрещенное в текущем состоянии.
    """

    def __init__(self, action_name: str, current_state: GameState) -> None:
        self.action_name = action_name
        self.current_state = current_state
        super().__init__(
            f"Действие '{action_name}' запрещено в текущем режиме игры '{current_state.value}'."
        )


class WorldStateNotBoundError(GameFlowError):
    """
    Действие требует активного WorldState, но он не был привязан к фасаду.
    """

    def __init__(self, action_name: str) -> None:
        self.action_name = action_name
        super().__init__(
            f"Действие '{action_name}' требует активного WorldState, но он не привязан "
            f"к GameFlowFacade - вызови bind_world_state() после старта или загрузки партии."
        )


# ==================================================================
# СТРАЖИ ПЕРЕХОДОВ (GUARD FUNCTIONS)
# ==================================================================

GuardFunction = Callable[[GameState, Optional[Any]], tuple[bool, Optional[str]]]


def guard_combat_payload_valid(
    from_state: GameState, payload: Optional[Any]
) -> tuple[bool, Optional[str]]:
    """
    Проверяет наличие корректного контекста для старта боя.
    """
    if not isinstance(payload, CombatTransitionPayload):
        return False, "для начала боя требуется передать CombatTransitionPayload"
    if payload.attacker_faction_id == payload.defender_faction_id:
        return False, "атакующий и защитник не могут быть одной и той же фракцией"
    return True, None


def guard_diplomacy_payload_valid(
    from_state: GameState, payload: Optional[Any]
) -> tuple[bool, Optional[str]]:
    """
    Проверяет наличие корректного контекста для открытия дипломатической сессии.
    """
    if not isinstance(payload, DiplomacyTransitionPayload):
        return (
            False,
            "для дипломатической сессии требуется передать DiplomacyTransitionPayload",
        )
    if payload.initiator_faction_id == payload.target_faction_id:
        return False, "нельзя открыть дипломатическую сессию с самим собой"
    return True, None


def guard_game_over_payload_valid(
    from_state: GameState, payload: Optional[Any]
) -> tuple[bool, Optional[str]]:
    """
    Проверяет наличие корректных данных об окончании игры.
    """
    if not isinstance(payload, GameOverPayload):
        return False, "для завершения игры требуется передать GameOverPayload"
    return True, None


# ==================================================================
# ПРОВЕРКИ РАЗРЕШЕНИЙ ДЕЙСТВИЙ
# ==================================================================


def is_diplomacy_action_allowed(state: GameState) -> bool:
    """
    Отправка писем и работа с послами разрешены только на глобальной карте.
    """
    return state in (GameState.STRATEGIC_MAP, GameState.DIPLOMATIC_SESSION)


def is_building_action_allowed(state: GameState) -> bool:
    """
    Строительство и снос зданий разрешены исключительно на глобальной карте.
    """
    return state == GameState.STRATEGIC_MAP


def is_recruitment_action_allowed(state: GameState) -> bool:
    """
    Найм и оснащение войск доступны только в стратегическом режиме.
    """
    return state == GameState.STRATEGIC_MAP


def is_saving_allowed(state: GameState) -> bool:
    """
    Сохранение состояния партии разрешено на глобальной карте или в меню паузы.
    """
    return state in (GameState.STRATEGIC_MAP, GameState.PAUSE)
