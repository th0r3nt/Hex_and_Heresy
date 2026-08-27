"""
Депеши, послы, переговоры и выплата дани.
"""

from fastapi import APIRouter

from src.back.l01_domain.factions.models.diplomacy.messengers import (
    Ambassador,
    Dispatch,
)
from src.back.l01_domain.factions.models.diplomacy.negotiations import (
    LLMDiplomaticResponse,
    NegotiationTranscript,
)
from src.back.l04_api.dependencies import Diplomacy, World
from src.back.l04_api.http.schemas.diplomacy import (
    AmbassadorRequest,
    AudienceSpeechRequest,
    DispatchRequest,
    TributeRequest,
    TributeResponse,
)

router = APIRouter(prefix="/diplomacy", tags=["diplomacy"])


# ====================================================
# Гонцы и послы
# ====================================================


@router.post("/dispatches", response_model=Dispatch)
async def send_dispatch(
    payload: DispatchRequest, diplomacy: Diplomacy, world: World
) -> Dispatch:
    """Нанимает гонца и отправляет письмо чужому лорду."""
    return await diplomacy.send_dispatch(
        world_state=world,
        sender_faction_id=payload.sender_faction_id,
        recipient_faction_id=payload.recipient_faction_id,
        message_text=payload.message_text,
    )


@router.post("/ambassadors", response_model=Ambassador)
async def send_ambassador(
    payload: AmbassadorRequest, diplomacy: Diplomacy, world: World
) -> Ambassador:
    """Отправляет посла в чужую цитадель."""
    return await diplomacy.send_ambassador(
        world_state=world,
        faction_id=payload.faction_id,
        name=payload.name,
        target_faction_id=payload.target_faction_id,
        traits=payload.traits,
        escort_army_id=payload.escort_army_id,
        negotiation_mode=payload.negotiation_mode,
        directive=payload.directive,
    )


@router.post("/ambassadors/{ambassador_id}/recall", response_model=Ambassador)
async def recall_ambassador(
    ambassador_id: str, diplomacy: Diplomacy, world: World
) -> Ambassador:
    """Аудиенция окончена: посол уходит домой."""
    return await diplomacy.recall_ambassador(world, ambassador_id)


# ====================================================
# Переговоры
# ====================================================


@router.post("/ambassadors/{ambassador_id}/speak", response_model=LLMDiplomaticResponse)
async def speak_to_lord(
    ambassador_id: str,
    payload: AudienceSpeechRequest,
    diplomacy: Diplomacy,
    world: World,
) -> LLMDiplomaticResponse:
    """Ручной режим аудиенции: игрок говорит от лица посла."""
    return await diplomacy.speak_to_lord(world, ambassador_id, payload.player_text)


@router.post(
    "/ambassadors/{ambassador_id}/auto-negotiate", response_model=NegotiationTranscript
)
async def run_auto_negotiation(
    ambassador_id: str, diplomacy: Diplomacy, world: World
) -> NegotiationTranscript:
    """Автоматический режим: посол торгуется по выданной директиве."""
    return await diplomacy.run_auto_negotiation(world, ambassador_id)


# ====================================================
# Дань
# ====================================================


@router.post("/tribute", response_model=TributeResponse)
async def pay_tribute(
    payload: TributeRequest, diplomacy: Diplomacy, world: World
) -> TributeResponse:
    """Закрывает выставленное требование дани."""
    amount = await diplomacy.pay_tribute(
        world_state=world,
        payer_faction_id=payload.payer_faction_id,
        receiver_faction_id=payload.receiver_faction_id,
    )
    return TributeResponse(amount_gold=amount)
