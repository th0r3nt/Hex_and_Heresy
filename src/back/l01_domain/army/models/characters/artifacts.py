"""
Артефакты героев — экипировка геройских карточек (3 слота: оружие,
броня, аксессуар). В отличие от Equipment, которая массово экипирует
обычные отряды из общего арсенала фракции, артефакт героя обычно
уникален и не тиражируется.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.army.constants import EquipmentSlot
from src.back.l01_domain.army.models.card.equipment import EquipmentStats


class HeroArtifact(BaseModel):
    """Предмет в одном из 3 слотов героя."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="Уникальный ID (напр. artifact_grom_cannonball)")
    name: str = Field(..., min_length=1)
    lore: str = Field(..., min_length=1)

    slot: EquipmentSlot = Field(...)
    tier: int = Field(..., ge=0, le=6)

    stats: EquipmentStats = Field(default_factory=EquipmentStats)

    is_unique: bool = Field(
        default=True, description="Найден в мире/уникален, не идёт в общий арсенал фракции"
    )
    cost_gold: float = Field(
        default=0.0, ge=0, description="Заполняется, если артефакт всё же можно заказать у оружейника"
    )
    cost_material: float = Field(default=0.0, ge=0)

    special_rules: Optional[str] = Field(default=None)