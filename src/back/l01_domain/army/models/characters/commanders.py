"""
Модель обычных и легендарных полководцев фракций.
"""

from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.common import MechanicalModifier

from src.back.l01_domain.exceptions import NegativeExperienceError


class CommanderGenerationType(str, Enum):
    """Способ появления полководца в игре (см. game_mechanics/commanders.md)."""

    PROCEDURAL = "procedural"  # [Раса] + [Архетип] + [Черта], собран случайно
    CUSTOM = "custom"  # Мастер игры (LLM) конвертировал биографию игрока в статы
    LEGENDARY = "legendary"  # Уникальная именная личность, вписанная в лор вручную


class CommanderArchetypeStats(BaseModel):
    """
    Математические модификаторы архетипа.

    При появлении нового архетипа с иной механикой -
    расширять этот блок.
    """

    model_config = ConfigDict(frozen=True)

    global_map_range_bonus: int = Field(
        default=0, description="Доп. дальность перемещения возглавляемой армии по глобальной карте (в гексах)"
    )
    melee_damage_modifier: float = Field(
        default=0.0,
        description="Модификатор урона армии в ближнем бою (доля, может быть отрицательным)",
    )
    ambush_resistance_modifier: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Снижение шанса армии попасть в засаду"
    )
    charge_damage_bonus: float = Field(
        default=0.0, description="Бонус к урону армии от 'Натиска'"
    )
    defense_stance_penalty: float = Field(
        default=0.0, description="Штраф к эффективности длительной обороны (темп x0)"
    )
    upkeep_gold_modifier: float = Field(
        default=1.0, gt=0, description="Множитель стоимости содержания армии (напр. 1.2 = +20%)"
    )
    initiative_modifier: int = Field(
        default=0,
        description="Модификатор инициативы полководца, если он появляется как Героическая карточка",
    )


class CommanderArchetype(BaseModel):
    """
    Шаблон архетипа (напр. 'Стратег', 'Параноик', 'Разжигатель войн').
    Один архетип переиспользуется между разными расами - задаёт только математику,
    не личность.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ..., min_length=1, description="Уникальный ID (напр. archetype_strategist)"
    )
    name: str = Field(..., min_length=1)
    description: str = Field(..., description="Краткое лорное описание архетипа")
    # Каждый архетип дает свои бонусы и ограничения
    stats: CommanderArchetypeStats = Field(default_factory=CommanderArchetypeStats)


class CommanderTrait(BaseModel):
    """
    Черта личности (напр. 'Труслив', 'Пишет стихи', 'Ненавидит эльфов').
    Ключевая деталь для LLM: формирует стиль речи в дипломатии и советах.
    Механический эффект необязателен - большинство черт чисто нарративные.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    text_fragment: str = Field(
        ..., description="Текст, вшиваемый в системный промпт полководца"
    )
    modifier: Optional[MechanicalModifier] = Field(default=None)


class CommanderCharacteristics(BaseModel):
    """
    Базовые характеристики полководца.
    """

    authority: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Авторитет - аура морали армии, вес слов в дипломатии",
    )
    tactical_acumen: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Тактическое чутьё - инициатива, качество советов игроку",
    )
    resilience: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Живучесть - сопротивление Страху, шанс выжить при ранении",
    )
    cunning: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Хитрость - успех засад, переговоров, вымогательства",
    )


class CommanderState(BaseModel):
    """
    Динамическое состояние полководца.
    """

    experience: int = Field(default=0, ge=0)
    level: int = Field(default=1, ge=1)
    is_alive: bool = Field(default=True)
    army_id: Optional[str] = Field(
        default=None, description="ID армии на глобальной карте, которой он сейчас командует"
    )


class Commander(BaseModel):
    """
    Агрегат полководца фракции.

    Собирается по формуле [Раса] + [Архетип] + [Черта] (процедурно),
    либо из биографии игрока через Game Master (custom),
    либо задан вручную как легендарная личность (legendary, см. heroic-уровень
    уникальности в commanders.md).
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1)
    faction_id: str = Field(..., description="ID фракции-нанимателя")

    generation_type: CommanderGenerationType = Field(...)
    archetype: CommanderArchetype = Field(...)
    trait: CommanderTrait = Field(...)
    characteristics: CommanderCharacteristics = Field(default_factory=CommanderCharacteristics)
    state: CommanderState = Field(default_factory=CommanderState)

    is_legendary: bool = Field(default=False)
    # Путь к вручную написанному промпту - только для legendary (см. prompt/builder.py)
    legendary_prompt_ref: Optional[str] = Field(default=None)
    # Несъёмный артефакт легендарного полководца (напр. ядро в животе Грома "Железное брюхо")
    fixed_equipment_ids: list[str] = Field(
        default_factory=list,
        description="ID предметов из Equipment-реестра, которые нельзя снять",
    )
    # Свободный текст биографии
    custom_biography: Optional[str] = Field(default=None)

    lore_description: str = Field(default="")

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def upkeep_gold_multiplier(self) -> float:
        """Итоговый множитель содержания армии от архетипа."""
        return self.archetype.stats.upkeep_gold_modifier

    def gain_experience(self, amount: int) -> None:
        """
        Начисляет опыт. Пороги левел-апа и связанный баланс - забота l02_services,
        домен только хранит инвариант 'опыт не может уменьшиться напрямую'.
        """

        if amount < 0:
            raise NegativeExperienceError(amount)
        self.state.experience += amount

    def assign_to_army(self, army_id: str) -> None:
        self.state.army_id = army_id

    def unassign_from_army(self) -> None:
        self.state.army_id = None
