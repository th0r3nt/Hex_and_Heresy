"""
Схемы параметров общих инструментов для всех ролей.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ReplyParams(BaseModel):
    """Параметры текстового ответа."""

    text: str = Field(
        ...,
        min_length=1,
        description="Текст прямого ответа собеседнику, правителю или персонажу",
    )


class StaySilentParams(BaseModel):
    """Параметры осознанного молчания."""

    reason: Optional[str] = Field(
        default=None, description="Причина, почему персонаж решил промолчать"
    )
