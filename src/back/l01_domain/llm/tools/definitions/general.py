"""
Определения общих инструментов для всех ролей.
"""

from src.back.l01_domain.llm.models.tools import ToolDefinition
from src.back.l01_domain.llm.tools.schemas.general import ReplyParams, StaySilentParams

REPLY = ToolDefinition(
    name="reply",
    description="Дать прямой художественный текстовый ответ собеседнику или правителю.",
    parameters_model=ReplyParams,
)

STAY_SILENT = ToolDefinition(
    name="stay_silent",
    description="Сохранить молчание и не совершать активных действий в этот ход.",
    parameters_model=StaySilentParams,
)
