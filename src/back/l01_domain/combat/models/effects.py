"""
Игровые модификаторы: профили местности и боевые эффекты.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.army.models.card.veterancy import MechanicalModifier
from src.back.l01_domain.combat.constants import (
    TerrainType,
    CombatEffectCategory,
    EffectStackingRule,
)


class TerrainProfile(BaseModel):
    """
    Игровые последствия конкретного типа местности.
    """

    model_config = ConfigDict(frozen=True)

    terrain_type: TerrainType = Field(...)
    movement_speed_modifier: float = Field(
        default=1.0, ge=0, description="Множитель скорости передвижения по клетке"
    )
    provides_ranged_cover: bool = Field(
        default=False, description="Даёт укрытие от дальнобойных атак (напр. лес)"
    ) # Укрытие дает 35% шанс уклонения
    breaks_formation: bool = Field(
        default=False, description="Ломает строй при входе (напр. лес, гора трупов)"
    )
    is_flammable: bool = Field(default=False, description="Можно поджечь магией/факелом")
    charge_penalty: float = Field(
        default=0.0,
        ge=0,
        le=1.0,
        description="Доля, на которую снижается бонус натиска на этой местности",
    )
    lore_description: str = Field(default="")


class CombatEffect(BaseModel):
    """
    Универсальный боевой эффект - статус на юните или клетке
    (горение, обморожение, страх, кровотечение, инфекция и т.д.).
    """

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    category: CombatEffectCategory = Field(...)

    duration_ticks: Optional[int] = Field(
        default=None, ge=0, description="None = действует до конца боя"
    )
    stacking_rule: EffectStackingRule = Field(default=EffectStackingRule.REFRESH)

    modifiers: list[MechanicalModifier] = Field(default_factory=list)

    removal_condition: Optional[str] = Field(
        default=None,
        description="Текстовое условие снятия, напр. 'снимается после выхода из леса'",
    )
