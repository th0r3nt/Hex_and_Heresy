"""
Схемы окна советника: плановое предложение, ответ игрока и свободный вопрос.
"""

from typing import Optional

from pydantic import BaseModel, Field

from src.back.l01_domain.factions.models.advisor import AdvisorProposal


class AdvisorProposalRequest(BaseModel):
    """
    Просьба интерфейса осмотреть державу на очередном глобальном такте.
    """

    faction_id: str = Field(..., min_length=1)
    force: bool = Field(
        default=False, description="Игнорировать паузу между советами (отладка)"
    )


class AdvisorProposalResponse(BaseModel):
    """
    Ответ советника на плановый осмотр.

    Предложение пусто, если повода для доклада нет, пауза между советами еще
    не вышла или советник выключен в настройках.
    """

    proposal: Optional[AdvisorProposal] = Field(default=None)


class AdvisorPendingResponse(BaseModel):
    """Открытые предложения фракции: интерфейс восстанавливает окно после F5."""

    proposals: list[AdvisorProposal] = Field(default_factory=list)


class AdvisorDecisionRequest(BaseModel):
    """
    Кнопка, которую нажал игрок под предложением.

    player_reply заполняется только для варианта «Дать свой ответ».
    """

    option_id: str = Field(..., min_length=1)
    player_reply: str = Field(default="", max_length=2000)


class AdvisorQuestionRequest(BaseModel):
    """
    Вопрос игрока советнику, заданный своими словами.
    """

    faction_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, max_length=2000)


class AdvisorToggleRequest(BaseModel):
    """
    Переключатель советника на экране настроек.
    """

    is_enabled: bool = Field(...)
