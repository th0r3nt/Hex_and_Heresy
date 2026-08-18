"""
Правитель фракции - определяет макро-стратегию (налоги, приоритеты
построек, дипломатическую позицию) и является "лицом" фракции в
дипломатии: именно к Lord'у приходят депеши и послы других фракций.

Важно: лорды не участвуют в бою напрямую, поэтому в отличие от
Commander у них нет боевых модификаторов - только тенденции при
автономных решениях (см. LordArchetypeStats).
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

from src.back.l01_domain.common import MechanicalModifier


class LordArchetypeStats(BaseModel):
    """
    Математические тенденции архетипа при автономных решениях лорда:
    установка налогов, приоритет застройки, поведение в дипломатии.
    """

    model_config = ConfigDict(frozen=True)

    tax_rate_bias: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Склонность повышать (+) или снижать (-) налоги относительно базового уровня",
    )
    military_building_priority: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Склонность отдавать строительные слоты военным зданиям, а не экономическим",
    )
    diplomatic_aggression: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Вероятность выбрать войну/вымогательство вместо переговоров при равных условиях",
    )
    bribery_susceptibility: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Насколько легко лорда переубедить золотом в дипломатии",
    )


class LordArchetype(BaseModel):
    """
    Шаблон архетипа лорда (напр. 'Тиран', 'Бюрократ', 'Фанатик').
    Один архетип переиспользуется между расами - задаёт только математику,
    не личность.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(..., description="Краткое лорное описание архетипа")
    stats: LordArchetypeStats = Field(default_factory=LordArchetypeStats)


class LordTrait(BaseModel):
    """
    Черта личности лорда. Формирует стиль речи в дипломатии и советах,
    механический эффект необязателен (см. commanders.py, CommanderTrait).
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    text_fragment: str = Field(..., description="Текст, вшиваемый в системный промпт лорда")
    modifier: Optional[MechanicalModifier] = Field(default=None)


class Lord(BaseModel):
    """
    Правитель фракции.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    faction_id: str = Field(...)
    name: str = Field(..., min_length=1)
    title: str = Field(
        ..., description="напр. 'Эрцгерцог', 'Судья', 'Вождь', 'Магистр Инквизиции'"
    )

    archetype: LordArchetype = Field(...)
    trait: LordTrait = Field(...)

    lore_description: str = Field(default="")

    @property
    def display_name(self) -> str:
        return f"{self.title} {self.name}"
