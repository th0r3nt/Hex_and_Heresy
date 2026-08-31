"""
Обработчики общих навыков, доступных любой роли.
"""

from typing import Any

from src.back.l01_domain.llm.tools.definitions.general import REPLY, STAY_SILENT
from src.back.l01_domain.llm.tools.schemas.general import ReplyParams, StaySilentParams
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor


class GeneralToolHandlers:
    """
    Речь и молчание: навыки без последствий для мира.

    Своих зависимостей у набора нет - ни фасадов, ни состояния: разговор
    целиком описывается параметрами вызова.
    """

    def register(self, executor: ToolExecutor) -> None:
        """
        Подключает общие навыки к исполнителю.
        """
        executor.register_handler(REPLY, self.reply)
        executor.register_handler(STAY_SILENT, self.stay_silent)

    # ====================================================
    # Навыки
    # ====================================================

    async def reply(
        self, params: ReplyParams, _ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Фиксирует прямой текстовый ответ собеседнику.
        """
        return params.text, {"reply": params.text}

    async def stay_silent(
        self, params: StaySilentParams, _ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Фиксирует осознанное молчание персонажа.
        """
        reason_detail = f": {params.reason}" if params.reason else ""
        return (
            f"Персонаж сохранил молчание{reason_detail}.",
            {"reason": params.reason or ""},
        )
