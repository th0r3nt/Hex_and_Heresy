"""
Модель обычных и легендарных полководцев фракций.
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
    StatName,
)
from src.back.l01_domain.exceptions.army import NegativeExperienceError

CommanderGenerationType = CharacterGenerationType


class CommanderTrait(Trait):
    """Черта характера полководца (наследует Trait для совместимости)."""

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


class CommanderCharacteristics(BaseModel):
    """Базовые числовые характеристики полководца (0..100)."""

    authority: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Авторитет: аура морали армии и вес слова в переговорах",
    )
    tactical_acumen: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Тактическое чутье: инициатива отрядов и качество донесений",
    )
    resilience: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Живучесть: сопротивление страху и стойкость в обороне",
    )
    cunning: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Хитрость: успех засад и скрытных маневров",
    )


class CommanderState(BaseModel):
    """Динамическое состояние полководца."""

    experience: int = Field(default=0, ge=0)
    level: int = Field(default=1, ge=1)
    is_alive: bool = Field(default=True)
    army_id: Optional[str] = Field(
        default=None, description="ID армии на глобальной карте под его командованием"
    )


class Commander(BaseModel):
    """Агрегат полководца фракции."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1)
    faction_id: str = Field(..., description="ID фракции-нанимателя")
    role_title: str = Field(
        default="Полководец",
        description="Воинское звание или роль (напр. Сержант стражи, Капитан лансьеров)",
    )

    generation_type: CharacterGenerationType = Field(
        default=CharacterGenerationType.PROCEDURAL
    )
    traits: list[Trait] = Field(default_factory=list)
    characteristics: CommanderCharacteristics = Field(default_factory=CommanderCharacteristics)
    state: CommanderState = Field(default_factory=CommanderState)

    is_legendary: bool = Field(default=False)
    legendary_prompt_ref: Optional[str] = Field(default=None)
    personality_prompt_override: Optional[str] = Field(
        default=None,
        description="Индивидуальный текст характера для кастомных полководцев",
    )
    fixed_equipment_ids: list[str] = Field(
        default_factory=list,
        description="ID предметов, которые нельзя снять (для легендарных личностей)",
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
            if "archetype" in data and data["archetype"] is not None:
                arch = data.pop("archetype")
                if isinstance(arch, dict) and "name" in arch:
                    data.setdefault("role_title", arch["name"])
                elif hasattr(arch, "name"):
                    data.setdefault("role_title", arch.name)
        return data

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def trait(self) -> Optional[Trait]:
        return self.traits[0] if self.traits else None

    @property
    def strategic_movement_bonus(self) -> int:
        """Бонус к дальности марша армии от активных черт."""
        bonus = 0
        for trait in self.traits:
            for mod in trait.modifiers:
                if mod.stat_name == StatName.MOVEMENT_SPEED:
                    bonus += int(mod.value)
        return bonus

    @property
    def vision_range_bonus(self) -> int:
        """Бонус к радиусу обзора армии от перков разведки в чертах полководца."""
        bonus = 0
        for trait in self.traits:
            for mod in trait.modifiers:
                if mod.stat_name == StatName.VISION_RANGE_HEXES:
                    bonus += int(mod.value)
        return bonus

    @property
    def upkeep_gold_multiplier(self) -> float:
        """Итоговый множитель содержания армии от черт."""
        multiplier = 1.0
        for trait in self.traits:
            for mod in trait.modifiers:
                if mod.stat_name == StatName.UPKEEP_GOLD:
                    multiplier += mod.value if mod.is_percentage else mod.value * 0.1
        return max(0.5, multiplier)

    def get_active_modifiers(self) -> list[MechanicalModifier]:
        """Возвращает все модификаторы от активных черт полководца."""
        modifiers: list[MechanicalModifier] = []
        for trait in self.traits:
            modifiers.extend(trait.modifiers)
        return modifiers

    def get_traits_prompt(self) -> str:
        """Возвращает форматированный блок черт для системного промпта."""
        return format_traits_prompt(self.traits)

    def gain_experience(self, amount: int) -> None:
        if amount < 0:
            raise NegativeExperienceError(amount)
        self.state.experience += amount

    def assign_to_army(self, army_id: str) -> None:
        self.state.army_id = army_id

    def unassign_from_army(self) -> None:
        self.state.army_id = None
