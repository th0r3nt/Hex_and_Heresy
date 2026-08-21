"""
Реестр оружия дальнего боя фракции людей.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    EquipmentSlot,
    EquipmentTag,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.humans.common import HumanWeaponId

_SLOT = EquipmentSlot.WEAPON

RANGED_WEAPONS: dict[str, dict[str, Any]] = {
    HumanWeaponId.IMPERIAL_CROSSBOW_01.value: {
        "id": HumanWeaponId.IMPERIAL_CROSSBOW_01.value,
        "name": "Имперские арбалеты",
        "lore": "Механическое оружие ополчения. Бьет сильно, но долгая и мучительная перезарядка делает стрелков уязвимыми.",
        "slot": _SLOT,
        "category": WeaponCategory.CROSSBOW,
        "tier": 1,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.STRING_BASED},
        "cost_gold": 2.0,
        "cost_material": 3.0,
        "stats": EquipmentStats(
            damage=12.0,
            range_hexes=6,
            initiative_modifier=-3,  # Штраф за долгую перезарядку
            armor_piercing=4.0,
        ),
    },
    HumanWeaponId.LONG_BOW_02.value: {
        "id": HumanWeaponId.LONG_BOW_02.value,
        "name": "Длинные луки",
        "lore": "Требуют большой физической силы и годов тренировок. Бьют дальше арбалетов и позволяют вести навесной огонь.",
        "slot": _SLOT,
        "category": WeaponCategory.BOW,
        "tier": 2,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.STRING_BASED},
        "cost_gold": 3.0,
        "cost_material": 2.0,
        "stats": EquipmentStats(
            damage=8.0,
            range_hexes=8,
            armor_piercing=1.0,
        ),
    },
    HumanWeaponId.HEAVY_ARQUEBUS_02.value: {
        "id": HumanWeaponId.HEAVY_ARQUEBUS_02.value,
        "name": "Тяжелые аркебузы",
        "lore": "Громко, больно, пахнет серой. Изобретение Железной пади, игнорирующее толщину эльфийских панцирей и шкуры огров.",
        "slot": _SLOT,
        "category": WeaponCategory.FIREARM,
        "tier": 2,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.BLACKPOWDER, EquipmentTag.HEAVY},
        "cost_gold": 6.0,
        "cost_material": 6.0,
        "stats": EquipmentStats(
            damage=18.0,
            range_hexes=5,
            stamina_drain_per_turn=1.0,
        ),
        "special_rules": "Пробитие брони: игнорирует 50% любой физической брони цели. Оглушительный залп: слегка снижает мораль слабодисциплинированных целей.",
    },
    HumanWeaponId.MULTI_BARREL_PISTOL_05.value: {
        "id": HumanWeaponId.MULTI_BARREL_PISTOL_05.value,
        "name": "Многоствольный пистоль",
        "lore": "Сложный инженерный механизм. Шесть стволов, вращающихся при выстреле, создают стену из свинца перед самым столкновением.",
        "slot": _SLOT,
        "category": WeaponCategory.FIREARM,
        "tier": 5,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.BLACKPOWDER},
        "cost_gold": 25.0,
        "cost_material": 15.0,
        "stats": EquipmentStats(
            damage=25.0,
            range_hexes=2,  # Оружие экстремально ближнего радиуса (залп почти в упор)
            armor_piercing=5.0,
            initiative_modifier=5,  # Выстрел всегда происходит быстрее взмаха меча
        ),
        "special_rules": "Шквал пуль: перед фазой ближнего боя отряд автоматически выпускает залп в упор, который нельзя заблокировать щитом.",
    },
}
