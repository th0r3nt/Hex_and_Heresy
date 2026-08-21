"""
Реестр оружия дальнего боя фракции баронских войск.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    EquipmentSlot,
    EquipmentTag,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.baronial_troops.common import BaronialWeaponId

_SLOT = EquipmentSlot.WEAPON

RANGED_WEAPONS: dict[str, dict[str, Any]] = {
    BaronialWeaponId.HEAVY_CROSSBOW_01.value: {
        "id": BaronialWeaponId.HEAVY_CROSSBOW_01.value,
        "name": "Тяжелые арбалеты",
        "lore": "Взводятся лебедкой целую вечность, зато короткий тяжелый болт прошивает даже орочьи черепа насквозь.",
        "slot": _SLOT,
        "category": WeaponCategory.CROSSBOW,
        "tier": 1,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.STRING_BASED, EquipmentTag.HEAVY},
        "cost_gold": 3.0,
        "cost_material": 4.0,
        "stats": EquipmentStats(
            damage=15.0,
            range_hexes=6,
            armor_piercing=6.0,
            initiative_modifier=-4,  # Очень долгая перезарядка
        ),
    },
    BaronialWeaponId.LINKED_CROSSBOW_06.value: {
        "id": BaronialWeaponId.LINKED_CROSSBOW_06.value,
        "name": "Сцепленный многоствольный самострел",
        "lore": "Крепится только к личной карете барона. Выкашивает толпы за один залп, но перезаряжается механически несколько тактов.",
        "slot": _SLOT,
        "category": WeaponCategory.SIEGE_ENGINE,
        "tier": 6,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.HEAVY},
        "cost_gold": 60.0,
        "cost_material": 80.0,
        "stats": EquipmentStats(
            damage=40.0,
            range_hexes=5,
            armor_piercing=15.0,
            initiative_modifier=-5,
        ),
        "special_rules": "Залповый огонь: наносит тяжелый урон целевому отряду и половину урона отрядам на соседних клетках.",
    },
}
