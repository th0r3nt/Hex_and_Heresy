"""
Общие доменные value-объекты, переиспользуемые в нескольких поддоменах
(army, factions, combat) - чтобы не тянуть их друг у друга.
"""

from pydantic import BaseModel, Field


class MechanicalModifier(BaseModel):
    """Математический бонус/штраф, полученный за подвиг/перк/архетип/вещь."""

    stat_name: str = Field(..., description="Имя изменяемого стата (morale, armor, damage)")
    value: float = Field(..., description="Значение (абсолютное или относительное)")
    is_percentage: bool = Field(default=False, description="Процентный ли модификатор")
