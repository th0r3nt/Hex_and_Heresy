"""
Физические и текстовые каналы дипломатической связи между фракциями:
- Dispatch - депеша (быстро, дёшево, перехватываемо)
- Ambassador - посол (медленно, персонализировано, рискованно)

(см. diplomacy.md)
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import AmbassadorStatus, NegotiationMode
from src.back.l01_domain.maps.models.strategic import HexCoordinates


class Dispatch(BaseModel):
    """
    Депеша - быстрое и дешёвое, но ограниченное текстовое сообщение
    между лордами двух фракций. Может быть перехвачена по пути. 
    (расчёт вероятности - забота l02_services, здесь только факт и виновник)
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    sender_faction_id: str = Field(...)
    recipient_faction_id: str = Field(...)
    message_text: str = Field(..., min_length=1)

    cost_gold: float = Field(default=0.0, ge=0)

    route: list[HexCoordinates] = Field(
        default_factory=list,
        description="Непройденный остаток пути гонца; последний гекс - цитадель получателя",
    )
    total_travel_ticks: int = Field(default=1, ge=0, description="Длина пути в тактах при отправке")
    travel_ticks_remaining: int = Field(default=1, ge=0)

    is_intercepted: bool = Field(default=False)
    intercepted_by_faction_id: Optional[str] = Field(default=None)


class Ambassador(BaseModel):
    """
    Посол - физический юнит на глобальной карте, 
    ведущий переговоры от имени фракции. 
    Личность генерируется процедурно, 
    но здесь хранится только то, что нужно для самой дипломатии.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    faction_id: str = Field(...)
    name: str = Field(..., min_length=1)
    traits: list[str] = Field(
        default_factory=list,
        description="напр. 'Красноречивый', 'Сноб' - влияют на текст переговоров",
    )

    status: AmbassadorStatus = Field(default=AmbassadorStatus.TRAVELING)
    escort_army_id: Optional[str] = Field(
        default=None, description="Армия сопровождения на глобальной карте, если выделена"
    )
    target_faction_id: Optional[str] = Field(default=None)

    current_hex: Optional[HexCoordinates] = Field(default=None)
    planned_path: list[HexCoordinates] = Field(
        default_factory=list, description="Непройденный остаток пути до чужой цитадели"
    )

    negotiation_mode: NegotiationMode = Field(default=NegotiationMode.AUTOMATIC)
    directive: Optional[str] = Field(
        default=None, description="Инструкция игрока, если выбран автоматический режим переговоров"
    )