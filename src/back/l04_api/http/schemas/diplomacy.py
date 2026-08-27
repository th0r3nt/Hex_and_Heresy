"""
Схемы депеш, послов, аудиенций и дани.
"""

from typing import Optional

from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import NegotiationMode


class DispatchRequest(BaseModel):
    """
    Письмо чужому лорду с гонцом.
    """

    sender_faction_id: str = Field(..., min_length=1)
    recipient_faction_id: str = Field(..., min_length=1)
    message_text: str = Field(..., min_length=1, max_length=4000)


class AmbassadorRequest(BaseModel):
    """
    Отправка посла в чужую цитадель.
    """

    faction_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=120)
    target_faction_id: str = Field(..., min_length=1)
    traits: Optional[list[str]] = Field(default=None)
    escort_army_id: Optional[str] = Field(default=None)
    negotiation_mode: NegotiationMode = Field(default=NegotiationMode.AUTOMATIC)
    directive: Optional[str] = Field(
        default=None, max_length=2000, description="Наказ послу для режима торга"
    )


class AudienceSpeechRequest(BaseModel):
    """
    Реплика игрока в ручном режиме аудиенции.
    """

    player_text: str = Field(..., min_length=1, max_length=4000)


class TributeRequest(BaseModel):
    """
    Выплата выставленного требования дани.
    """

    payer_faction_id: str = Field(..., min_length=1)
    receiver_faction_id: str = Field(..., min_length=1)


class TributeResponse(BaseModel):
    """
    Итог выплаты. Ноль означает, что требования дани не было.
    """

    amount_gold: float = Field(default=0.0, ge=0)
