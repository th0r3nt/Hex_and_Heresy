"""
Окно советника: плановое предложение, ответ на кнопку и свободный диалог.

Молчание советника - это его ответ, а не ошибка запроса: пустое предложение
приезжает обычным 200. А вот обращение к выключенному советнику - ошибка:
интерфейс не должен открывать окно, которого игрок не включал.
"""

from fastapi import APIRouter

from src.back.l01_domain.factions.models.advisor import AdvisorAnswer, AdvisorDecision
from src.back.l04_api.dependencies import Advisor, World
from src.back.l04_api.http.schemas.advisor import (
    AdvisorDecisionRequest,
    AdvisorPendingResponse,
    AdvisorProposalRequest,
    AdvisorProposalResponse,
    AdvisorQuestionRequest,
    AdvisorToggleRequest,
)
from src.back.l04_api.http.schemas.common import OperationResult

router = APIRouter(prefix="/advisor", tags=["advisor"])


# ====================================================
# Пассивная инициатива
# ====================================================


@router.post("/proposals", response_model=AdvisorProposalResponse)
async def offer_proposal(
    payload: AdvisorProposalRequest, advisor: Advisor, world: World
) -> AdvisorProposalResponse:
    """
    Советник осматривает державу и, если есть повод, приносит предложение.
    """
    proposal = await advisor.offer_proposal(
        world_state=world,
        faction_id=payload.faction_id,
        force=payload.force,
    )
    return AdvisorProposalResponse(proposal=proposal)


@router.get("/proposals", response_model=AdvisorPendingResponse)
async def list_pending_proposals(
    faction_id: str, advisor: Advisor
) -> AdvisorPendingResponse:
    """Предложения, на которые игрок еще не ответил."""
    return AdvisorPendingResponse(proposals=advisor.pending_proposals(faction_id))


@router.post("/proposals/{proposal_id}/answer", response_model=AdvisorDecision)
async def answer_proposal(
    proposal_id: str,
    payload: AdvisorDecisionRequest,
    advisor: Advisor,
    world: World,
) -> AdvisorDecision:
    """
    Игрок нажал кнопку под предложением: советник отвечает и берется за дело.
    """
    return await advisor.answer_proposal(
        world_state=world,
        proposal_id=proposal_id,
        option_id=payload.option_id,
        player_reply=payload.player_reply,
    )


# ====================================================
# Диалоговый режим
# ====================================================


@router.post("/chat", response_model=AdvisorAnswer)
async def ask_advisor(
    payload: AdvisorQuestionRequest, advisor: Advisor, world: World
) -> AdvisorAnswer:
    """Вопрос игрока советнику в свободной форме."""
    return await advisor.ask(
        world_state=world,
        faction_id=payload.faction_id,
        question=payload.question,
    )


# ====================================================
# Настройка
# ====================================================


@router.put("/enabled", response_model=OperationResult)
async def set_advisor_enabled(
    payload: AdvisorToggleRequest, advisor: Advisor
) -> OperationResult:
    """Включает или выключает советника: игра идет и без него."""
    advisor.set_enabled(payload.is_enabled)
    state = "включен" if payload.is_enabled else "выключен"
    return OperationResult(detail=f"Советник {state}.")
