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


class MechanicalModifier(BaseModel):
    """Математический бонус/штраф, полученный за подвиг/перк/архетип/вещь."""

    stat_name: str = Field(..., description="Имя изменяемого стата (morale, armor, damage)")
    value: float = Field(..., description="Значение (абсолютное или относительное)")
    is_percentage: bool = Field(default=False, description="Процентный ли модификатор")
