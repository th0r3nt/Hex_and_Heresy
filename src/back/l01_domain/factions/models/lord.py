"""
Правитель фракции — определяет макро-стратегию и ведет дипломатические переговоры.
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

from src.back.l01_domain.common import CharacterGenerationType, MechanicalModifier


class LordArchetypeStats(BaseModel):
    """
    Математические тенденции архетипа при автономных решениях лорда.
    """

    model_config = ConfigDict(frozen=True)

    tax_rate_bias: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Склонность повышать (+) или снижать (-) налоги",
    )
    military_building_priority: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Склонность отдавать строительные слоты военным зданиям",
    )
    diplomatic_aggression: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Вероятность выбрать войну или вымогательство вместо переговоров",
    )
    bribery_susceptibility: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Насколько легко лорда переубедить золотом в дипломатии",
    )


class LordArchetype(BaseModel):
    """
    Шаблон архетипа лорда (например, 'Тиран', 'Бюрократ', 'Фанатик').
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(..., description="Краткое лорное описание архетипа")
    stats: LordArchetypeStats = Field(default_factory=LordArchetypeStats)


class LordTrait(BaseModel):
    """
    Черта личности лорда.
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
        ..., description="Например, 'Эрцгерцог', 'Судья', 'Вождь', 'Магистр Инквизиции'"
    )

    generation_type: CharacterGenerationType = Field(
        default=CharacterGenerationType.PROCEDURAL
    )
    archetype: LordArchetype = Field(...)
    trait: LordTrait = Field(...)

    is_legendary: bool = Field(default=False)
    legendary_prompt_ref: Optional[str] = Field(default=None)
    personality_prompt_override: Optional[str] = Field(
        default=None,
        description="Сгенерированный мастером игры текст характера для кастомного лорда",
    )
    custom_biography: Optional[str] = Field(
        default=None, description="Исходный текст биографии от игрока"
    )

    lore_description: str = Field(default="")

    @property
    def display_name(self) -> str:
        return f"{self.title} {self.name}"
