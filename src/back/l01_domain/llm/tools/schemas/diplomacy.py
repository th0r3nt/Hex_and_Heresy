"""
Схемы параметров инструментов дипломатических переговоров и соглашений.
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import NegotiationMode, ResourceType


class DeclareWarParams(BaseModel):
    """Параметры объявления войны."""

    reason: Optional[str] = Field(
        default=None, description="Официальная причина объявления войны"
    )


class MakePeaceParams(BaseModel):
    """Параметры заключения мира."""

    terms_summary: Optional[str] = Field(
        default=None, description="Краткое описание мирных договоренностей"
    )


class ProposeTradeParams(BaseModel):
    """Параметры торгового соглашения."""

    give_resource: ResourceType = Field(..., description="Отдаваемый ресурс")
    give_amount: float = Field(..., gt=0, description="Количество отдаваемого ресурса за такт")
    get_resource: ResourceType = Field(..., description="Получаемый взамен ресурс")
    get_amount: float = Field(..., gt=0, description="Количество получаемого ресурса за такт")
    duration_turns: int = Field(
        default=5, ge=1, description="Длительность торгового соглашения в тактах"
    )


class EstablishBordersParams(BaseModel):
    """Параметры пакта о ненападении и разграничении территорий."""

    allowed_hex_ids: list[str] = Field(
        default_factory=list, description="Список идентификаторов согласованных гексов границы"
    )


class EstablishRightOfPassageParams(BaseModel):
    """Параметры предоставления права прохода армий."""

    toll_gold_per_crossing: float = Field(
        default=0.0, ge=0, description="Плата золотом за каждое пересечение гекса"
    )
    duration_turns: int = Field(
        default=5, ge=1, description="Срок действия права прохода в тактах"
    )
    allowed_hex_ids: list[str] = Field(
        default_factory=list, description="Разрешенные для транзита гексы"
    )


class DemandTributeParams(BaseModel):
    """Параметры вымогательства дани."""

    gold_amount: float = Field(..., gt=0, description="Требуемая сумма золотом")


class ExecuteAmbassadorParams(BaseModel):
    """Параметры казни посла на аудиенции."""

    reason: Optional[str] = Field(
        default=None, description="Причина вынесения смертного приговора"
    )


class SendDispatchParams(BaseModel):
    """Параметры отправки письма-депеши с гонцом."""

    recipient_faction_id: str = Field(..., min_length=1, description="Фракция-получатель")
    message_text: str = Field(..., min_length=1, description="Текст письма")


class SendAmbassadorParams(BaseModel):
    """Параметры отправки дипломатического посла."""

    name: str = Field(..., min_length=1, description="Имя посла")
    target_faction_id: str = Field(..., min_length=1, description="Целевая фракция")
    traits: Optional[list[str]] = Field(default=None, description="Черты характера посла")
    escort_army_id: Optional[str] = Field(
        default=None, description="Идентификатор армии охраны"
    )
    negotiation_mode: NegotiationMode = Field(
        default=NegotiationMode.AUTOMATIC,
        description="Режим переговоров: manual или automatic",
    )
    directive: Optional[str] = Field(
        default=None, description="Директива и рамки торга для посла"
    )


class RecallAmbassadorParams(BaseModel):
    """Параметры отзыва посла домой."""

    ambassador_id: str = Field(..., min_length=1, description="Идентификатор посла")


class PayTributeParams(BaseModel):
    """Параметры выплаты требуемой дани."""

    receiver_faction_id: str = Field(..., min_length=1, description="Фракция-получатель дани")
