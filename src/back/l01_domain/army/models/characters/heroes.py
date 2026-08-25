"""
Модель геройских карточек - уникальных боевых единиц с деревом навыков,
слотами артефактов и механикой травм (см. game_mechanics/heroic cards.md).
"""

from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.army.models.characters.artifacts import HeroArtifact
from src.back.l01_domain.common import MechanicalModifier
from src.back.l01_domain.army.constants import MAX_HERO_LEVEL

from src.back.l01_domain.exceptions.army import HeroLevelTooLowError


class HeroArchetype(BaseModel):
    """
    Уникальный архетип героя (напр. 'Неубиваемый' у Грома "Железное брюхо").
    В отличие от CommanderArchetype - почти всегда пишется вручную под
    конкретного героя и не переиспользуется между персонажами.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(..., description="Лорное описание архетипа")
    special_rule: str = Field(
        ...,
        description="Текст уникальной механики (напр. 'Второе дыхание после смертельного ранения')",
    )
    # Если спецправило сводится к понятному числовому эффекту - фиксируем и его,
    # текстовое описание при этом остаётся источником истины для LLM
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
    """Шрам - постоянный след тяжёлого ранения. Шрамы у героя складываются."""

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
        default=0, ge=0, description="Сколько тактов герой ещё выбыл после тяжёлого ранения"
    )
    attached_squad_id: Optional[str] = Field(
        default=None, description="ID отряда, к которому прикреплён герой (командует им)"
    )
    scars: list[Scar] = Field(default_factory=list)


class Hero(BaseModel):
    """
    Агрегат геройской карточки.
    Занимает 1 гекс на тактической карте, изначально по силе сравним с отрядом ~100 бойцов.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1)
    faction_id: str = Field(...)

    archetype: HeroArchetype = Field(...)
    max_hp: float = Field(..., gt=0)

    # 3 слота артефактов
    weapon: Optional[HeroArtifact] = Field(default=None)
    armor: Optional[HeroArtifact] = Field(default=None)
    accessory: Optional[HeroArtifact] = Field(default=None)

    chosen_perks: list[Perk] = Field(
        default_factory=list,
        description="Перки, выбранные по мере левел-апа (не более одного на уровень)",
    )

    state: HeroState = Field(...)
    lore_description: str = Field(default="")

    @classmethod
    def create_new(
        cls, name: str, faction_id: str, archetype: HeroArchetype, max_hp: float
    ) -> "Hero":
        """
        Фабричный метод создания свежего героя на полном здоровье.
        """

        return cls(
            name=name,
            faction_id=faction_id,
            archetype=archetype,
            max_hp=max_hp,
            state=HeroState(current_hp=max_hp),
        )

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def is_attached(self) -> bool:
        return self.state.attached_squad_id is not None

    def get_active_modifiers(self) -> list[MechanicalModifier]:
        """
        Собирает все действующие модификаторы героя: перки + шрамы + спецправило
        архетипа (если оно числовое). Используется l02_services при расчёте
        боевых статов и при аггрегации бонусов для отряда, к которому прикреплён герой.
        """

        modifiers = [perk.modifier for perk in self.chosen_perks]
        modifiers.extend(scar.modifier for scar in self.state.scars)
        if self.archetype.trigger_modifier is not None:
            modifiers.append(self.archetype.trigger_modifier)
        return modifiers

    def attach_to_squad(self, squad_id: str) -> None:
        """Прикрепляет героя к обычному отряду ('свита') - герой начинает им командовать."""
        self.state.attached_squad_id = squad_id

    def detach_from_squad(self) -> None:
        self.state.attached_squad_id = None

    def take_damage(self, raw_damage: float, armor_piercing: float = 0.0) -> bool:
        """
        Наносит урон герою. Возвращает True, если HP упало до 0.

        Бросок '90% шанс тяжёлого ранения вместо смерти' и генерация текста
        шрама через LLM - зона ответственности l02_services (там же рандом
        и вызов инфраструктуры). Домен только фиксирует падение HP до нуля.
        """

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
        """
        Переводит героя в статус 'Тяжело ранен' вместо смерти и добавляет шрам.
        Вызывается сервисом после успешного броска на выживание.
        """

        self.state.is_heavily_wounded = True
        self.state.wounded_ticks_remaining = recovery_ticks
        self.state.scars.append(scar)
        self.state.is_alive = True
        self.state.current_hp = max(self.state.current_hp, 1.0)

    def learn_perk(self, perk: Perk) -> None:
        """
        Добавляет выбранный перк. Проверка 'ровно 1 перк на конкретный уровень,
        а не просто level >= required' - забота вызывающего сервиса,
        здесь базовый инвариант по минимальному уровню.
        """

        if perk.level_required > self.state.level:
            raise HeroLevelTooLowError(
                current_level=self.state.level,
                required_level=perk.level_required,
                perk_id=perk.id,
            )
        self.chosen_perks.append(perk)
