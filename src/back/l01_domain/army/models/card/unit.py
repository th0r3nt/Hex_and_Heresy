"""
Базовые схемы характеристик отдельного бойца и шаблона расового юнита.
"""

from pydantic import BaseModel, Field, ConfigDict


class BaseUnitStats(BaseModel):
    """Базовые физические и ментальные параметры одного бойца без экипировки."""

    model_config = ConfigDict(frozen=True)

    max_hp: float = Field(..., gt=0, description="Максимальное здоровье одного бойца в отряде")
    base_armor: float = Field(
        default=0.0, ge=0, description="Врождённая броня (напр. шкура, чешуя)"
    )
    base_speed: float = Field(
        default=2.0, gt=0, description="Базовая скорость перемещения (в квадратах)"
    )
    base_morale: float = Field(
        default=50.0, ge=0, le=100, description="Базовая дисциплина/мораль"
    )
    base_stamina: float = Field(default=100.0, ge=0, le=100, description="Запас сил")
    base_initiative: int = Field(default=10, description="Инициатива в очереди ходов")


class UnitArchetype(BaseModel):
    """Шаблон юнита из gamedata (например: 'Городская стража')."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Уникальный ID шаблона (напр. unit_greenskins_boyz)")
    faction_id: str = Field(..., description="ID фракции (например, greenskins, humans)")
    name: str = Field(..., min_length=1, description="Название базового юнита")
    tier: int = Field(..., ge=0, le=6, description="Тир юнита (0-6)")
    default_unit_count: int = Field(
        ..., gt=0, description="Стандартное количество бойцов в отряде"
    )


    # Требования к содержанию за 1 бойца в такт
    base_upkeep_food: float = Field(default=1.0, ge=0)
    base_upkeep_gold: float = Field(default=0.0, ge=0)

    lore_description: str = Field(default="", description="Описание отряда из лора")
