"""
Модель обычных и легендарных полководцев фракций.
"""

from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.common import CharacterGenerationType, MechanicalModifier
from src.back.l01_domain.exceptions.army import NegativeExperienceError

# Для обратной совместимости
CommanderGenerationType = CharacterGenerationType


class CommanderArchetypeStats(BaseModel):
    """
    Математические модификаторы архетипа.
    """

    model_config = ConfigDict(frozen=True)

    strategic_map_range_bonus: int = Field(
        default=0,
        description="Дополнительная дальность перемещения возглавляемой армии по глобальной карте (в гексах)",
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
        default=1.0,
        gt=0,
        description="Множитель стоимости содержания армии (например, 1.2 = +20%)",
    )
    initiative_modifier: int = Field(
        default=0,
        description="Модификатор инициативы полководца, если он появляется как героическая карточка",
    )


class CommanderArchetype(BaseModel):
    """
    Шаблон архетипа (например, 'Стратег', 'Параноик', 'Разжигатель войн').
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ..., min_length=1, description="Уникальный ID (например, archetype_strategist)"
    )
    name: str = Field(..., min_length=1)
    description: str = Field(..., description="Краткое лорное описание архетипа")
    stats: CommanderArchetypeStats = Field(default_factory=CommanderArchetypeStats)


class CommanderTrait(BaseModel):
    """
    Черта личности полководца.
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
        description="Авторитет — аура морали армии, вес слов в дипломатии",
    )
    tactical_acumen: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Тактическое чутье — инициатива отрядов, качество советов игроку",
    )
    resilience: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Живучесть — сопротивление страху, шанс выжить при ранении",
    )
    cunning: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Хитрость — успех засад, переговоров, вымогательства",
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
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1)
    faction_id: str = Field(..., description="ID фракции-нанимателя")

    generation_type: CharacterGenerationType = Field(
        default=CharacterGenerationType.PROCEDURAL
    )
    archetype: CommanderArchetype = Field(...)
    trait: CommanderTrait = Field(...)
    characteristics: CommanderCharacteristics = Field(default_factory=CommanderCharacteristics)
    state: CommanderState = Field(default_factory=CommanderState)

    is_legendary: bool = Field(default=False)
    legendary_prompt_ref: Optional[str] = Field(default=None)
    personality_prompt_override: Optional[str] = Field(
        default=None,
        description="Текст характера для полководца (либо генерируется гейм мастером, либо берется лорный из .md файла личности)",
    )
    fixed_equipment_ids: list[str] = Field(
        default_factory=list,
        description="ID предметов из реестра экипировки, которые нельзя снять",
    )
    custom_biography: Optional[str] = Field(
        default=None, description="Исходный текст биографии от игрока"
    )

    lore_description: str = Field(default="")

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def upkeep_gold_multiplier(self) -> float:
        """Итоговый множитель содержания армии от архетипа."""
        return self.archetype.stats.upkeep_gold_modifier

    def gain_experience(self, amount: int) -> None:
        if amount < 0:
            raise NegativeExperienceError(amount)
        self.state.experience += amount

    def assign_to_army(self, army_id: str) -> None:
        self.state.army_id = army_id

    def unassign_from_army(self) -> None:
        self.state.army_id = None
