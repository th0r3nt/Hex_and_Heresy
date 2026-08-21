"""
Реестр оружия дальнего боя фракции зеленокожих.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    EquipmentSlot,
    EquipmentTag,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.greenskins.common import GreenskinsWeaponId

_SLOT = EquipmentSlot.WEAPON

RANGED_WEAPONS: dict[str, dict[str, Any]] = {
    GreenskinsWeaponId.DART_BUNDLE_01.value: {
        "id": GreenskinsWeaponId.DART_BUNDLE_01.value,
        "name": "Связка дротиков",
        "lore": "Дешево и сердито. Гоблины кидают их целыми охапками. Половина летит мимо, но если попадет — радости нет предела.",
        "slot": _SLOT,
        "category": WeaponCategory.THROWING,
        "tier": 1,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 0.0,
        "cost_material": 1.0,
        "stats": EquipmentStats(
            damage=6.0,
            range_hexes=3,
        ),
        "special_rules": "Врожденная косоглазие: есть 30% шанс полного промаха по цели.",
    },
    GreenskinsWeaponId.STOLEN_BOMBS_03.value: {
        "id": GreenskinsWeaponId.STOLEN_BOMBS_03.value,
        "name": "Украденные метательные бомбы",
        "lore": "Железные шары, начиненные черным порохом. Орки не умеют рассчитывать длину фитиля, поэтому взрываются они очень непредсказуемо.",
        "slot": _SLOT,
        "category": WeaponCategory.THROWING,
        "tier": 3,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.BLACKPOWDER},
        "cost_gold": 5.0,
        "cost_material": 6.0,
        "stats": EquipmentStats(
            damage=20.0,
            armor_piercing=10.0,
            range_hexes=4,
        ),
        "special_rules": "Взрывная волна: сплеш-урон по гексу. Может подорваться прямо в руках при броске (осечка).",
    },
    GreenskinsWeaponId.STOLEN_MUSKET_03.value: {
        "id": GreenskinsWeaponId.STOLEN_MUSKET_03.value,
        "name": "Спертый имперский мушкет",
        "lore": "Когда-то это было элегантное оружие стрелковых рот. Теперь к нему примотали гвозди, а порох засыпают горстями на глаз.",
        "slot": _SLOT,
        "category": WeaponCategory.FIREARM,
        "tier": 3,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.BLACKPOWDER},
        "cost_gold": 4.0,
        "cost_material": 5.0,
        "stats": EquipmentStats(
            damage=22.0,
            armor_piercing=15.0,
            range_hexes=6,
            initiative_modifier=-2,
        ),
        "special_rules": "Стрельба наугад: дальность больше, чем у обычных аркебуз (6 гексов), но штраф к меткости колоссальный.",
    },
}
