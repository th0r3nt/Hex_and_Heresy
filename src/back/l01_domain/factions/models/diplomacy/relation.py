"""
Агрегат состояния отношений между двумя конкретными фракциями -
собирает воедино все действующие между ними пакты.
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import DiplomaticStance
from src.back.l01_domain.factions.models.diplomacy.pacts import (
    TradeAgreement,
    NonAggressionPact,
    RightOfPassagePact,
    VassalPact,
    IntelligenceSharingPact,
    HostageExchangePact,
    WarAlliancePact,
)


class DiplomaticRelation(BaseModel):
    """Состояние отношений между двумя конкретными фракциями."""

    faction_a_id: str = Field(...)
    faction_b_id: str = Field(...)
    stance: DiplomaticStance = Field(default=DiplomaticStance.PEACE)

    trade_agreement: Optional[TradeAgreement] = Field(default=None)
    non_aggression_pact: Optional[NonAggressionPact] = Field(default=None)
    right_of_passage: Optional[RightOfPassagePact] = Field(default=None)
    vassal_pact: Optional[VassalPact] = Field(default=None)
    intelligence_sharing: Optional[IntelligenceSharingPact] = Field(default=None)
    hostage_exchange: Optional[HostageExchangePact] = Field(default=None)
    war_alliance: Optional[WarAlliancePact] = Field(default=None)

    tribute_demanded_gold: Optional[float] = Field(default=None, ge=0)

    def declare_war(self) -> None:
        self.stance = DiplomaticStance.WAR
        self.trade_agreement = None
        self.non_aggression_pact = None
        self.right_of_passage = None
        self.vassal_pact = None
        self.intelligence_sharing = None
        self.hostage_exchange = (
            None  # исполнение казни заложника - забота слушателя события в l02_services
        )
        self.war_alliance = None

    # =====================================================================================
    # Методы, которые будут вызываться через JSON-схемы Function Calling
    # =====================================================================================

    # Мир
    def make_peace(self) -> None:
        self.stance = DiplomaticStance.PEACE

    # Торговля
    def propose_trade(self, agreement: TradeAgreement) -> None:
        if self.stance == DiplomaticStance.WAR:
            raise ValueError("cannot trade while at war")
        self.trade_agreement = agreement

    # Право прохода
    def establish_right_of_passage(self, pact: RightOfPassagePact) -> None:
        if self.stance == DiplomaticStance.WAR:
            raise ValueError("cannot grant passage while at war")
        self.right_of_passage = pact

    # Вассалитет
    def form_vassalage(self, pact: VassalPact) -> None:
        if self.stance == DiplomaticStance.WAR:
            raise ValueError("cannot form vassalage while at war")
        self.vassal_pact = pact

    # Обмен разведданными
    def share_intelligence(self, pact: IntelligenceSharingPact) -> None:
        if self.stance == DiplomaticStance.WAR:
            raise ValueError("cannot share intelligence while at war")
        self.intelligence_sharing = pact

    # Обмен заложниками как гарантия мира
    def exchange_hostages(self, pact: HostageExchangePact) -> None:
        if self.stance == DiplomaticStance.WAR:
            raise ValueError("cannot exchange hostages while at war")
        self.hostage_exchange = pact

    # Военный союз
    def form_war_alliance(self, pact: WarAlliancePact) -> None:
        if self.stance == DiplomaticStance.WAR:
            raise ValueError(
                "cannot form a war alliance while already at war with this faction"
            )
        self.war_alliance = pact
