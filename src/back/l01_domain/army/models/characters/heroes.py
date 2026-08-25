"""
Модель геройских карточек — уникальных боевых единиц с деревом навыков,
слотами артефактов и механикой травм.
"""

from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.army.models.characters.artifacts import HeroArtifact
from src.back.l01_domain.common import CharacterGenerationType, MechanicalModifier
from src.back.l01_domain.army.constants import MAX_HERO_LEVEL
from src.back.l01_domain.exceptions.army import HeroLevelTooLowError


class HeroArchetype(BaseModel):
    """
    Уникальный архетип героя.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(..., description="Лорное описание архетипа")
    special_rule: str = Field(
        ...,
        description="Текст уникальной механики",
    )
    trigger_modifier: Optional[MechanicalModifier] = Field(default=None)


class Perk(BaseModel):
    """
    Узел дерева навыков. На каждом уровне (1–20) игрок выбирает 1 из 2 перков.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(...)
    level_required: int = Field(..., ge=1, le=MAX_HERO_LEVEL)
    modifier: MechanicalModifier = Field(...)
    text_fragment: str = Field(
        ..., description="Текст, дополняющий системный промпт героя при выборе перка"
    )


class Scar(BaseModel):
    """Шрам — постоянный след тяжелого ранения. Шрамы у героя складываются."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., min_length=1)
    description: str = Field(...)
    modifier: MechanicalModifier = Field(...)


class HeroState(BaseModel):
    """Динамическое состояние героя."""

    experience: int = Field(default=0, ge=0)
    level: int = Field(default=1, ge=1, le=MAX_HERO_LEVEL)
    current_hp: float = Field(..., ge=0)
    is_alive: bool = Field(default=True)
    is_heavily_wounded: bool = Field(default=False)
    wounded_ticks_remaining: int = Field(
        default=0, ge=0, description="Сколько тактов герой еще выбыл после тяжелого ранения"
    )
    attached_squad_id: Optional[str] = Field(
        default=None, description="ID отряда, к которому прикреплен герой (командует им)"
    )
    scars: list[Scar] = Field(default_factory=list)


class Hero(BaseModel):
    """
    Агрегат геройской карточки.
    Занимает 1 гекс на тактической карте, по силе сопоставим с отрядом солдат.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1)
    faction_id: str = Field(...)

    generation_type: CharacterGenerationType = Field(
        default=CharacterGenerationType.PROCEDURAL
    )
    archetype: HeroArchetype = Field(...)
    max_hp: float = Field(..., gt=0)

    # 3 слота артефактов
    weapon: Optional[HeroArtifact] = Field(default=None)
    armor: Optional[HeroArtifact] = Field(default=None)
    accessory: Optional[HeroArtifact] = Field(default=None)

    chosen_perks: list[Perk] = Field(
        default_factory=list,
        description="Перки, выбранные по мере левел-апа",
    )

    state: HeroState = Field(...)

    is_legendary: bool = Field(default=False)
    legendary_prompt_ref: Optional[str] = Field(default=None)
    personality_prompt_override: Optional[str] = Field(
        default=None,
        description="Сгенерированный мастером игры текст характера для кастомного героя",
    )
    custom_biography: Optional[str] = Field(
        default=None, description="Исходный текст биографии от игрока"
    )

    lore_description: str = Field(default="")

    @classmethod
    def create_new(
        cls,
        name: str,
        faction_id: str,
        archetype: HeroArchetype,
        max_hp: float,
        generation_type: CharacterGenerationType = CharacterGenerationType.PROCEDURAL,
        custom_biography: Optional[str] = None,
        personality_prompt_override: Optional[str] = None,
        is_legendary: bool = False,
        legendary_prompt_ref: Optional[str] = None,
    ) -> "Hero":
        """Фабричный метод создания нового героя."""
        return cls(
            name=name,
            faction_id=faction_id,
            archetype=archetype,
            max_hp=max_hp,
            generation_type=generation_type,
            custom_biography=custom_biography,
            personality_prompt_override=personality_prompt_override,
            is_legendary=is_legendary,
            legendary_prompt_ref=legendary_prompt_ref,
            state=HeroState(current_hp=max_hp),
        )

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def is_attached(self) -> bool:
        return self.state.attached_squad_id is not None

    def get_active_modifiers(self) -> list[MechanicalModifier]:
        modifiers = [perk.modifier for perk in self.chosen_perks]
        modifiers.extend(scar.modifier for scar in self.state.scars)
        if self.archetype.trigger_modifier is not None:
            modifiers.append(self.archetype.trigger_modifier)
        return modifiers

    def attach_to_squad(self, squad_id: str) -> None:
        self.state.attached_squad_id = squad_id

    def detach_from_squad(self) -> None:
        self.state.attached_squad_id = None

    def take_damage(self, raw_damage: float, armor_piercing: float = 0.0) -> bool:
        effective_armor = 0.0
        if self.armor:
            effective_armor += self.armor.stats.armor_bonus
        if self.accessory:
            effective_armor += self.accessory.stats.armor_bonus
        effective_armor = max(0.0, effective_armor - armor_piercing)

        net_damage = max(0.0, raw_damage - effective_armor)
        self.state.current_hp = max(0.0, self.state.current_hp - net_damage)

        return self.state.current_hp <= 0

    def apply_scar(self, scar: Scar, recovery_ticks: int) -> None:
        self.state.is_heavily_wounded = True
        self.state.wounded_ticks_remaining = recovery_ticks
        self.state.scars.append(scar)
        self.state.is_alive = True
        self.state.current_hp = max(self.state.current_hp, 1.0)

    def learn_perk(self, perk: Perk) -> None:
        if perk.level_required > self.state.level:
            raise HeroLevelTooLowError(
                current_level=self.state.level,
                required_level=perk.level_required,
                perk_id=perk.id,
            )
        self.chosen_perks.append(perk)
