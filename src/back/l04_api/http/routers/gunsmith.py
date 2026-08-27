"""
Чертежи снаряжения: заказ мастеру и одобрение готового чертежа.
"""

from fastapi import APIRouter

from src.back.l04_api.dependencies import Gunsmith, World
from src.back.l04_api.http.schemas.common import OperationResult
from src.back.l04_api.http.schemas.gunsmith import (
    BlueprintApproveRequest,
    BlueprintDraftRequest,
    BlueprintDraftResponse,
)

router = APIRouter(prefix="/gunsmith", tags=["gunsmith"])


@router.post("/blueprints/draft", response_model=BlueprintDraftResponse)
async def draft_blueprint(
    payload: BlueprintDraftRequest, gunsmith: Gunsmith, world: World
) -> BlueprintDraftResponse:
    """
    Мастер обдумывает заказ правителя.

    Отказ - это не ошибка запроса, а ответ мастера, поэтому он приезжает
    обычным 200 с пустым чертежом и объяснением в реплике.
    """
    draft, master_reply = await gunsmith.draft_blueprint(
        world_state=world,
        faction_id=payload.faction_id,
        user_request=payload.user_request,
    )
    return BlueprintDraftResponse(
        is_approved=draft is not None,
        master_reply=master_reply,
        draft=draft,
    )


@router.post("/blueprints/approve", response_model=OperationResult)
async def approve_blueprint(
    payload: BlueprintApproveRequest, gunsmith: Gunsmith, world: World
) -> OperationResult:
    """
    Игрок соглашается с чертежом: списывается разработка, чертеж уходит в арсенал.
    """
    await gunsmith.approve_blueprint(
        world_state=world,
        faction_id=payload.faction_id,
        draft=payload.draft,
    )
    return OperationResult(detail=f"Чертеж «{payload.draft.name}» принят в арсенал.")
