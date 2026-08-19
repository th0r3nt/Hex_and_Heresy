"""
Конечный автомат состояний игрового процесса (GameFlowFSM).
"""

from typing import Any, Optional

from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l02_services.gameflow.guards import (
    GuardConditionFailedError,
    InvalidStateTransitionError,
)
from src.back.l02_services.gameflow.states import GameFlowTrigger, GameState
from src.back.l02_services.gameflow.transitions import TRANSITION_MATRIX


class GameFlowFSM:
    """
    Конечный автомат, управляющий глобальным состоянием игры.
    Обеспечивает валидацию переходов через стражей, ведет стек истории
    для возврата из модальных окон (пауза, настройки) и уведомляет подписчиков.
    """

    def __init__(
        self,
        initial_state: GameState = GameState.MAIN_MENU,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._current_state = initial_state
        self._state_stack: list[GameState] = []
        self._event_bus = event_bus
        self._current_payload: Optional[Any] = None

    @property
    def current_state(self) -> GameState:
        """
        Текущее состояние игрового процесса.
        """
        return self._current_state

    @property
    def current_payload(self) -> Optional[Any]:
        """
        Контекст данных текущего состояния.
        """
        return self._current_payload

    def can_trigger(self, trigger: GameFlowTrigger, payload: Optional[Any] = None) -> bool:
        """
        Проверяет возможность перехода без его фактического выполнения.
        """

        rule = TRANSITION_MATRIX.get((self._current_state, trigger))
        if rule is None:
            return False

        for guard in rule.guards:
            passed, _reason = guard(self._current_state, payload)
            if not passed:
                return False
        return True

    async def trigger(
        self, trigger: GameFlowTrigger, payload: Optional[Any] = None
    ) -> GameState:
        """
        Выполняет переход по триггеру с валидацией стражей.
        Выбрасывает сооветствующие ошибки при несоблюдении.
        """

        rule = TRANSITION_MATRIX.get((self._current_state, trigger))
        if rule is None:
            raise InvalidStateTransitionError(self._current_state, trigger)

        for guard in rule.guards:
            passed, reason = guard(self._current_state, payload)
            if not passed:
                raise GuardConditionFailedError(reason or "условие перехода не выполнено")

        previous_state = self._current_state

        # Обработка возврата из стека для паузы и настроек
        if trigger in (GameFlowTrigger.RESUME_GAME, GameFlowTrigger.CLOSE_SETTINGS):
            target_state = self._state_stack.pop() if self._state_stack else rule.target_state
        else:
            if rule.saves_to_history:
                self._state_stack.append(self._current_state)
            target_state = rule.target_state

        self._current_state = target_state
        self._current_payload = payload

        # Если возвращаемся в главное меню, очищаем стек истории
        if self._current_state == GameState.MAIN_MENU:
            self._state_stack.clear()

        if self._event_bus is not None:
            await self._event_bus.publish(
                "gameflow.state_changed",
                from_state=previous_state,
                to_state=self._current_state,
                trigger=trigger,
                payload=payload,
            )

        return self._current_state
