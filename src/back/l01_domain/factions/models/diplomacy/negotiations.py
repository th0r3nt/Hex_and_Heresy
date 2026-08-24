"""
DTO переговоров с лордом чужой фракции.

Лорд отвечает строго структурированным JSON: художественный текст плюс
необязательное дипломатическое действие (Function Calling из diplomacy.md).
Здесь описан только контракт ответа; переносом действия на агрегат
DiplomaticRelation занимается l02_services.
"""

from typing import Optional

from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import (
    DiplomaticActionType,
    ResourceType,
)


class DiplomaticAction(BaseModel):
    """
    Решение лорда и его параметры. Схема намеренно плоская: строгий JSON-режим
    провайдеров плохо переваривает union-ы, а лишние поля просто игнорируются.
    """

    kind: DiplomaticActionType = Field(default=DiplomaticActionType.NONE)

    give_resource: Optional[ResourceType] = Field(
        default=None, description="Что отдает инициатор переговоров (propose_trade)"
    )
    give_amount: float = Field(default=0.0, ge=0)
    get_resource: Optional[ResourceType] = Field(
        default=None, description="Что инициатор получает взамен (propose_trade)"
    )
    get_amount: float = Field(default=0.0, ge=0)

    gold_amount: float = Field(
        default=0.0,
        ge=0,
        description="Размер дани или пошлины за проход, если решение о золоте",
    )
    duration_turns: int = Field(default=5, ge=1, description="Срок действия договора в тактах")
    allowed_hex_ids: list[str] = Field(
        default_factory=list, description="Гексы для договора о границах или права прохода"
    )


class LLMDiplomaticResponse(BaseModel):
    """Ожидаемый JSON-ответ лорда на письмо или реплику посла."""

    reply_text: str = Field(..., description="Что лорд говорит вслух")
    action: Optional[DiplomaticAction] = Field(
        default=None, description="Дипломатическое решение, если лорд его принял"
    )


class NegotiationLine(BaseModel):
    """Одна реплика в стенограмме переговоров."""

    speaker: str = Field(..., description="'ambassador' или 'lord'")
    text: str = Field(...)


class NegotiationTranscript(BaseModel):
    """Итог автоматических переговоров двух нейросетей."""

    lines: list[NegotiationLine] = Field(default_factory=list)
    final_response: Optional[LLMDiplomaticResponse] = Field(default=None)
