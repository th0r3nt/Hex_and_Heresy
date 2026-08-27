"""
Исполнитель действий советника.

ЗАГЛУШКА. Советник управляет державой только через навыки Function Calling,
а их схемы еще не написаны. Пока реестр обработчиков пуст, и
любое намерение советника возвращается игроку со статусом NOT_SUPPORTED.

Когда навыки появятся, корню компоновки останется зарегистрировать здесь
обработчики - по одному на навык, каждый поверх своего фасада (TurnsFacade,
GunsmithFacade, агрегатов Faction и ConstructedBuilding). Менять сам
исполнитель для этого не придется.
"""

from typing import Any, Awaitable, Callable

from src.back.l01_domain.exceptions.base import DomainError
from src.back.l01_domain.factions.models.advisor import (
    AdvisorAction,
    AdvisorActionOutcome,
    AdvisorActionStatus,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.logger import main_logger

# Обработчик навыка: применяет изменения к миру и возвращает строку для игрока
AdvisorActionHandler = Callable[[WorldState, str, dict[str, Any]], Awaitable[str]]


class AdvisorActionExecutor:
    """
    Переносит намерения советника на игровой мир.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, AdvisorActionHandler] = {}

    # ==================================================================
    # РЕЕСТР НАВЫКОВ
    # ==================================================================

    def register(self, tool_name: str, handler: AdvisorActionHandler) -> None:
        """
        Подключает обработчик навыка. Повторная регистрация заменяет прежний.
        """
        self._handlers[tool_name] = handler

    def supports(self, tool_name: str) -> bool:
        return tool_name in self._handlers

    @property
    def known_tools(self) -> list[str]:
        return sorted(self._handlers)

    # ==================================================================
    # ИСПОЛНЕНИЕ
    # ==================================================================

    async def execute(
        self,
        world_state: WorldState,
        faction_id: str,
        action: AdvisorAction,
    ) -> AdvisorActionOutcome:
        """
        Выполняет одно намерение советника.

        Наружу ничего не бросает: отчет о неудаче - такая же часть ответа
        игроку, как и успех. Красный экран вместо реплики советника игрок
        получить не должен.
        """
        handler = self._handlers.get(action.tool_name)

        if handler is None:
            main_logger.warning(
                f"[Advisor] Навык '{action.tool_name}' не подключен к исполнителю."
            )
            return AdvisorActionOutcome(
                action=action,
                status=AdvisorActionStatus.NOT_SUPPORTED,
                detail=f"Советник пока не умеет выполнять '{action.tool_name}'.",
            )

        try:
            detail = await handler(world_state, faction_id, action.arguments)
        except DomainError as error:
            main_logger.warning(
                f"[Advisor] Навык '{action.tool_name}' отклонен миром: {error.message}"
            )
            return AdvisorActionOutcome(
                action=action,
                status=AdvisorActionStatus.FAILED,
                detail=error.message,
            )

        return AdvisorActionOutcome(
            action=action,
            status=AdvisorActionStatus.EXECUTED,
            detail=detail,
        )

    async def execute_all(
        self,
        world_state: WorldState,
        faction_id: str,
        actions: list[AdvisorAction],
    ) -> list[AdvisorActionOutcome]:
        """
        Выполняет намерения советника по порядку.
        """
        return [
            await self.execute(world_state, faction_id, action) for action in actions
        ]
