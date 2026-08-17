"""
Модели предметов экипировки: оружие, броня, аксессуары.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.army.constants import EquipmentSlot


class EquipmentStats(BaseModel):
    """
    Модификаторы характеристик, даваемые экипировкой.
    """

    model_config = ConfigDict(frozen=True)

    # Дополнительный урон
    damage: float = Field(default=0.0, ge=0, description="Базовый урон")
    # Дополнительная защита
    armor_piercing: float = Field(
        default=0.0, ge=0, description="Игнорирование брони цели (в ед.)"
    )
    armor_bonus: float = Field(default=0.0, ge=0, description="Бонус к броне")
    # Дополнительная дальность
    range_hexes: int = Field(default=1, ge=1, description="Дальность атаки в гексах/квадратах")
    # Модификатор скорости
    speed_modifier: float = Field(
        default=0.0, description="Модификатор скорости (-0.2 = -20%)"
    )
    # Модификатор инициативы
    initiative_modifier: int = Field(default=0, description="Модификатор очередности хода")
    # Дополнительный расход выносливости на ход
    stamina_drain_per_turn: float = Field(
        default=0.0, ge=0, description="Доп. расход выносливости за ход"
    )


class Equipment(BaseModel):
    """
    Базовая модель любого предмета экипировки.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ..., min_length=1, description="Уникальный ID (напр. human_weapon_halberd_02)"
    )
    name: str = Field(..., min_length=1, description="Название предмета")
    lore: str = Field(..., min_length=1, description="Лор предмета")

    slot: EquipmentSlot = Field(..., description="Слот экипировки")
    tier: int = Field(..., ge=0, le=6, description="Тир предмета (0-6)")

    # Каждый предмет выбирает, что будет давать юниту
    # Например, дефолт оружие будет давать только урон
    stats: EquipmentStats = Field(default_factory=EquipmentStats)

    # Экономика производства
    cost_gold: float = Field(default=0.0, ge=0)
    cost_material: float = Field(default=0.0, ge=0)

    is_custom: bool = Field(default=False, description="Создано ли оружейником-LLM")
    special_rules: Optional[str] = Field(
        default=None, description="Текстовое описание кастомных механик"
    )
