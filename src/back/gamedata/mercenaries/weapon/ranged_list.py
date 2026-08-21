"""
Реестр оружия дальнего боя фракции наемников.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    EquipmentSlot,
    EquipmentTag,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.mercenaries.common import MercenaryWeaponId

_SLOT = EquipmentSlot.WEAPON

RANGED_WEAPONS: dict[str, dict[str, Any]] = {
    MercenaryWeaponId.COMPANY_CROSSBOW_01.value: {
        "id": MercenaryWeaponId.COMPANY_CROSSBOW_01.value,
        "name": "Украденные казенные арбалеты",
        "lore": "Дезертиры забрали лучшее оружие из имперских арсеналов. Надежное, мощное и хорошо смазанное.",
        "slot": _SLOT,
        "category": WeaponCategory.CROSSBOW,
        "tier": 1,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.STRING_BASED},
        "cost_gold": 5.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(
            damage=12.0,
            range_hexes=6,
            armor_piercing=5.0,
        ),
    },
    MercenaryWeaponId.AERIAL_BOMBS_03.value: {
        "id": MercenaryWeaponId.AERIAL_BOMBS_03.value,
        "name": "Авиабомбы корсаров",
        "lore": "Бочки с порохом и гвоздями, которые гоблины-дезертиры сбрасывают прямо с палубы зависшего дирижабля.",
        "slot": _SLOT,
        "category": WeaponCategory.SIEGE_ENGINE,
        "tier": 3,
        "tags": {EquipmentTag.BLACKPOWDER, EquipmentTag.HEAVY},
        "cost_gold": 15.0,
        "cost_material": 20.0,
        "stats": EquipmentStats(
            damage=30.0,
            range_hexes=4,  # Сброс идет по области под дирижаблем
            armor_piercing=15.0,
        ),
        "special_rules": "Бомбардировка (AoE): дирижабль сбрасывает бомбы каждый такт боя. Урон бьет по большой площади, но не точен.",
    },
}
