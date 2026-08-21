"""
Реестр оружия ближнего боя фракции наемников.
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

MELEE_WEAPONS: dict[str, dict[str, Any]] = {
    MercenaryWeaponId.BEAR_CLAWS_01.value: {
        "id": MercenaryWeaponId.BEAR_CLAWS_01.value,
        "name": "Когти и челюсти",
        "lore": "Врожденное оружие боевых медведей. Одним ударом лапы ломают рыцарские щиты пополам.",
        "slot": _SLOT,
        "category": WeaponCategory.NATURAL,
        "tier": 1,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.SHIELD_BREAKER},
        "cost_gold": 0.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(
            damage=15.0,
            armor_piercing=5.0,
        ),
    },
    MercenaryWeaponId.HEROIC_ARSENAL_02.value: {
        "id": MercenaryWeaponId.HEROIC_ARSENAL_02.value,
        "name": "Сборный героический арсенал",
        "lore": "Магический меч, гномий топор и посох жреца. Каждый бьет своим стилем, но вместе они выкашивают целые взводы. Но откуда здесь гном?",
        "slot": _SLOT,
        "category": WeaponCategory.SWORD,
        "tier": 2,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 0.0,  # Оружие уже их собственное
        "cost_material": 0.0,
        "stats": EquipmentStats(
            damage=40.0,  # Огромный урон на 4-х человек
            armor_piercing=10.0,
            initiative_modifier=5,
        ),
        "special_rules": "Сыгранность: атаки наносят комбинированный урон (игнорирует сопротивления).",
    },
}
