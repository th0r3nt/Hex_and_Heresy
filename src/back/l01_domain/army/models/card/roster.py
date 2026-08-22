"""
Ростер найма: рецепты сборки отрядов фракции.
"""

from typing import Optional
from pydantic import BaseModel, Field


class RosterEntry(BaseModel):
    """
    Рецепт найма отряда в ростере фракции.
    Описывает, из каких компонентов состоит итоговый отряд и сколько стоит его найм.
    """

    id: str = Field(..., description="Уникальный ID рецепта (напр. roster_human_halberdiers)")
    faction_id: str = Field(..., description="ID фракции, которой принадлежит рецепт")
    unit_archetype_id: str = Field(..., description="ID базового архетипа юнита")

    weapon_id: Optional[str] = Field(default=None, description="ID выдаваемого оружия")
    armor_id: Optional[str] = Field(default=None, description="ID выдаваемой брони")
    accessory_id: Optional[str] = Field(default=None, description="ID выдаваемого аксессуара")

    cost_gold: float = Field(default=0.0, ge=0, description="Стоимость найма в золоте")
    cost_material: float = Field(default=0.0, ge=0, description="Стоимость найма в материалах")
