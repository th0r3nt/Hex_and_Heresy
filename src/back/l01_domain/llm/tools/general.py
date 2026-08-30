"""
Общие инструменты для всех ролей.
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.llm.models.skills import ToolDefinition


class ReplyParams(BaseModel):
    """Параметры текстового ответа."""

    text: str = Field(
        ..., min_length=1, description="Текст прямого ответа собеседнику, правителю или персонажу/персонажам"
    )


class StaySilentParams(BaseModel):
    """Параметры осознанного молчания."""

    reason: Optional[str] = Field(
        default=None, description="Причина, почему персонаж решил промолчать"
    )


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
