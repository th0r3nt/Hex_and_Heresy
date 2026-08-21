"""
Реестр оружия дальнего боя и магических фокусов фракции 'Паства метеорита'.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    EquipmentSlot,
    EquipmentTag,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.congregation_of_the_meteorite.common import CotmWeaponId

_SLOT = EquipmentSlot.WEAPON

RANGED_WEAPONS: dict[str, dict[str, Any]] = {
    CotmWeaponId.NECROSIS_STAFF_04.value: {
        "id": CotmWeaponId.NECROSIS_STAFF_04.value,
        "name": "Жезл некроза",
        "lore": "Посох призывателя мумий. Выпускает сгустки концентрированной смерти, разъедающей плоть.",
        "slot": _SLOT,
        "category": WeaponCategory.MAGIC,
        "tier": 4,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.CURSED, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 15.0,
        "cost_material": 40.0,
        "stats": EquipmentStats(
            damage=15.0,
            range_hexes=5,
            armor_piercing=10.0,
        ),
        "special_rules": "Поднятие павших: каждый убитый выстрелом этого жезла враг мгновенно превращается в зомби, встающего на сторону Паствы до конца боя.",
    },
    CotmWeaponId.PROGENITOR_FLAME_05.value: {
        "id": CotmWeaponId.PROGENITOR_FLAME_05.value,
        "name": "Пламя Прародителя",
        "lore": "Дыхание Алчного дракона. Абсолютное уничтожение. Огонь, который не гаснет, пока не пожрет всё.",
        "slot": _SLOT,
        "category": WeaponCategory.NATURAL,
        "tier": 5,
        "tags": {EquipmentTag.RESONITE_POWERED, EquipmentTag.FLAMMABLE},
        "cost_gold": 0.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(
            damage=50.0,
            range_hexes=4,
            armor_piercing=30.0,
        ),
        "special_rules": "Огненный шторм (AoE): наносит магический урон по площади. Оставляет гекс горящим.",
    },
}
