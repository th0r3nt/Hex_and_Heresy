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
    NEUTRALS = "neutrals"


class CharacterGenerationType(str, Enum):
    """Способ появления персонажа в игре."""

    PROCEDURAL = "procedural"
    CUSTOM = "custom"
    LEGENDARY = "legendary"


class StatName(str, Enum):
    """Характеристики, которые может изменять MechanicalModifier."""

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
    VISION_RANGE_HEXES = "vision_range_hexes"
    HP_DRAIN_PER_TICK = "hp_drain_per_tick"
    MAGIC_DISABLED = "magic_disabled"
    UPKEEP_GOLD = "upkeep_gold"


class MechanicalModifier(BaseModel):
    """Математический бонус или штраф, полученный за подвиг, перк или черту."""

    stat_name: StatName = Field(..., description="Изменяемая характеристика")
    value: float = Field(..., description="Значение бонуса или штрафа")
    is_percentage: bool = Field(default=False, description="Процентный ли модификатор")
