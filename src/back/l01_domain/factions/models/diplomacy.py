"""
Дипломатия между фракциями: 
депеши (быстро, дёшево, перехватываемо) 
и послы (медленно, персонализировано, рискованно) 
- см. diplomacy.md.
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import (
    ResourceType,
    DiplomaticStance,
    AmbassadorStatus,
    NegotiationMode,
)


class Dispatch(BaseModel):
    """
    Депеша - быстрое и дешёвое, но ограниченное текстовое сообщение
    между лордами двух фракций. Может быть перехвачена по пути (расчёт
    вероятности - забота l02_services, здесь только факт и виновник).
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    sender_faction_id: str = Field(...)
    recipient_faction_id: str = Field(...)
    message_text: str = Field(..., min_length=1)

    cost_gold: float = Field(default=0.0, ge=0)
    travel_ticks_remaining: int = Field(default=1, ge=0)

    is_intercepted: bool = Field(default=False)
    intercepted_by_faction_id: Optional[str] = Field(default=None)


class Ambassador(BaseModel):
    """
    Посол - физический юнит на глобальной карте, ведущий переговоры от
    имени фракции. Личность генерируется как у кастомного полководца, но
    здесь хранится только то, что нужно для самой дипломатии.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    faction_id: str = Field(...)
    name: str = Field(..., min_length=1)
    traits: list[str] = Field(
        default_factory=list,
        description="напр. 'Красноречивый', 'Сноб' - влияют на текст переговоров",
    )

    status: AmbassadorStatus = Field(default=AmbassadorStatus.TRAVELING)
    escort_squad_id: Optional[str] = Field(default=None)
    target_faction_id: Optional[str] = Field(default=None)

    negotiation_mode: NegotiationMode = Field(default=NegotiationMode.AUTOMATIC)
    directive: Optional[str] = Field(
        default=None, description="Инструкция игрока, если выбран автоматический режим переговоров"
    )


class TradeAgreement(BaseModel):
    """Условия пассивного обмена ресурсами между двумя фракциями."""

    give_resource: ResourceType = Field(...)
    give_amount: float = Field(..., ge=0)
    get_resource: ResourceType = Field(...)
    get_amount: float = Field(..., ge=0)

    duration_turns: int = Field(..., ge=1)
    remaining_turns: int = Field(...)


class NonAggressionPact(BaseModel):
    """
    Договор о ненападении - юниты не могут заходить на чужие гексы без объявления войны.
    """

    allowed_hex_ids: list[str] = Field(default_factory=list)


class DiplomaticRelation(BaseModel):
    """Состояние отношений между двумя конкретными фракциями."""

    faction_a_id: str = Field(...)
    faction_b_id: str = Field(...)
    stance: DiplomaticStance = Field(default=DiplomaticStance.PEACE)

    trade_agreement: Optional[TradeAgreement] = Field(default=None)
    non_aggression_pact: Optional[NonAggressionPact] = Field(default=None)
    tribute_demanded_gold: Optional[float] = Field(default=None, ge=0)

    def declare_war(self) -> None:
        self.stance = DiplomaticStance.WAR
        self.trade_agreement = None
        self.non_aggression_pact = None

    def make_peace(self) -> None:
        self.stance = DiplomaticStance.PEACE

    def propose_trade(self, agreement: TradeAgreement) -> None:
        if self.stance == DiplomaticStance.WAR:
            raise ValueError("cannot trade while at war")
        self.trade_agreement = agreement
