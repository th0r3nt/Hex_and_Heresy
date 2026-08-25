"""
Общие доменные сущности и value-объекты, переиспользуемые в нескольких
поддоменах (army, factions, combat, world).
"""

from enum import Enum
from pydantic import BaseModel, Field


class FactionRace(str, Enum):
    """Базовые расы и культурные архетипы мира Hex & Heresy."""

    HUMANS = "humans"
    GREENSKINS = "greenskins"
    ELFS = "elfs"
    BARONIAL_TROOPS = "baronial_troops"
    CONGREGATION_OF_THE_METEORITE = "congregation_of_the_meteorite"
    MERCENARIES = "mercenaries"


class CharacterGenerationType(str, Enum):
    """Способ появления персонажа в игре."""

    PROCEDURAL = "procedural"  # Собран процедурно
    CUSTOM = "custom"  # Сгенерирован мастером игры на основе биографии игрока
    LEGENDARY = "legendary"  # Уникальная лорная личность, созданная вручную


class StatName(str, Enum):
    """Характеристики, которые может задевать MechanicalModifier."""

    MORALE = "morale"
    ARMOR = "armor"
    DAMAGE = "damage"
    SPEED = "speed"
    INITIATIVE = "initiative"
    HP_REGEN = "hp_regen"
    AMBUSH_RESISTANCE = "ambush_resistance"
    RANGED_ACCURACY = "ranged_accuracy"
    FIREARM_MISFIRE_CHANCE = "firearm_misfire_chance"
    MOVEMENT_SPEED = "movement_speed"
    VISIBILITY_RANGE_CELLS = "visibility_range_cells"
    HP_DRAIN_PER_TICK = "hp_drain_per_tick"
    MAGIC_DISABLED = "magic_disabled"


class MechanicalModifier(BaseModel):
    """Математический бонус или штраф, полученный за подвиг, перк, архетип или вещь."""

    stat_name: StatName = Field(
        ..., description="Изменяемый стат (morale, armor, damage, ...)"
    )
    value: float = Field(..., description="Значение (абсолютное или относительное)")
    is_percentage: bool = Field(default=False, description="Процентный ли модификатор")
