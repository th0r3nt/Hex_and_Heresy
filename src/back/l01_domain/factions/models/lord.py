"""
Правитель фракции: определяет макро-стратегию и ведет дипломатические переговоры.
"""

from typing import Any, Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.back.l01_domain.army.models.characters.traits import (
    Trait,
    TraitCategory,
    format_traits_prompt,
)
from src.back.l01_domain.common import (
    CharacterGenerationType,
    MechanicalModifier,
)


class LordTrait(Trait):
    """Черта характера лорда (наследует Trait для совместимости)."""

    category: TraitCategory = TraitCategory.PSYCHOLOGICAL
    prompt_text: str = Field(default="")

    def __init__(self, **data: Any) -> None:
        if "text_fragment" in data and "prompt_text" not in data:
            data["prompt_text"] = data["text_fragment"]
        if "category" not in data:
            data["category"] = TraitCategory.PSYCHOLOGICAL
        if "modifier" in data:
            mod = data.pop("modifier")
            if mod is not None:
                data.setdefault("modifiers", [mod])
        super().__init__(**data)

    @property
    def text_fragment(self) -> str:
        return self.prompt_text

    @property
    def modifier(self) -> Optional[MechanicalModifier]:
        return self.modifiers[0] if self.modifiers else None


# ====================================================
# Стратегический характер правителя
# ====================================================


class LordStrategicBias(BaseModel):
    """
    Стратегические уклоны правителя: числовая проекция его характера на
    решения об экономике и внешней политике.

    Эти же числа приезжают из ответа мастера игры при разборе биографии
    от игрока, поэтому у легендарных и процедурных лордов они одинаковые.
    """

    model_config = ConfigDict(frozen=True)

    tax_rate_bias: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Склонность двигать налоговый ползунок вверх (1.0) или вниз (-1.0)",
    )
    military_building_priority: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
        description="Приоритет военной застройки против экономической",
    )
    diplomatic_aggression: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Агрессивность во внешней политике: 0.0 - миротворец, 1.0 - завоеватель",
    )
    bribery_susceptibility: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Сговорчивость при подкупе золотом на переговорах",
    )


class Lord(BaseModel):
    """Правитель фракции."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    faction_id: str = Field(...)
    name: str = Field(..., min_length=1)
    title: str = Field(
        default="Лорд",
        description="Титул: Канцлер, Судья, Вождь, Магистр Инквизиции и т.д.",
    )

    generation_type: CharacterGenerationType = Field(
        default=CharacterGenerationType.PROCEDURAL
    )
    traits: list[Trait] = Field(default_factory=list)

    is_legendary: bool = Field(default=False)
    legendary_prompt_ref: Optional[str] = Field(default=None)
    personality_prompt_override: Optional[str] = Field(
        default=None,
        description="Индивидуальный текст характера для кастомного правителя",
    )
    custom_biography: Optional[str] = Field(
        default=None, description="Исходный текст биографии от игрока"
    )
    lore_description: str = Field(default="")

    bias: LordStrategicBias = Field(
        default_factory=LordStrategicBias,
        description="Стратегический характер правителя в числах",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "trait" in data and data["trait"] is not None:
                t = data.pop("trait")
                traits_list = data.setdefault("traits", [])
                if t not in traits_list:
                    traits_list.append(t)
            if "archetype" in data:
                data.pop("archetype")
        return data

    @property
    def display_name(self) -> str:
        return f"{self.title} {self.name}".strip()

    @property
    def trait(self) -> Optional[Trait]:
        return self.traits[0] if self.traits else None

    def get_active_modifiers(self) -> list[MechanicalModifier]:
        modifiers: list[MechanicalModifier] = []
        for trait in self.traits:
            modifiers.extend(trait.modifiers)
        return modifiers

    def get_traits_prompt(self) -> str:
        return format_traits_prompt(self.traits)
