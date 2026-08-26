"""
Правитель фракции: определяет макро-стратегию и ведет дипломатические переговоры.
"""

from typing import Any, Optional
from uuid import uuid4
from pydantic import BaseModel, Field, model_validator

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
