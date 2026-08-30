"""
Обработчики общих навыков.

Мир они не трогают: слово и молчание - тоже полноценный ход модели, просто
без последствий. Регистрировать их нужно затем, чтобы у роли всегда был
законный способ не делать ничего: иначе она начнет выдумывать действия,
лишь бы вызвать хоть какой-нибудь навык.
"""

from src.back.l01_domain.llm.tools.general import (
    REPLY,
    STAY_SILENT,
    ReplyParams,
    StaySilentParams,
)
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor


async def _reply(context: ToolExecutionContext, params: ReplyParams) -> str:
    return params.text


async def _stay_silent(
    context: ToolExecutionContext, params: StaySilentParams
) -> str:
    return params.reason or "Модель не нашла повода вмешиваться."


def register_general_handlers(executor: ToolExecutor) -> None:
    """
    Подключает общие навыки к диспетчеру.
    """
    executor.register(REPLY, _reply)
    executor.register(STAY_SILENT, _stay_silent)


__all__ = ["register_general_handlers"]
