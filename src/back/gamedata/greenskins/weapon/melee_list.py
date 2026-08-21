"""
Реестр оружия ближнего боя фракции зеленокожих.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    EquipmentSlot,
    EquipmentTag,
    UnitSizeCategory,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.greenskins.common import GreenskinsWeaponId

_SLOT = EquipmentSlot.WEAPON

MELEE_WEAPONS: dict[str, dict[str, Any]] = {
    GreenskinsWeaponId.SHARPENED_STICK_00.value: {
        "id": GreenskinsWeaponId.SHARPENED_STICK_00.value,
        "name": "Заостренные палки",
        "lore": "Просто ветка. Если ткнуть ею в глаз рыцарю, ему будет неприятно. В остальных случаях — мусор.",
        "slot": _SLOT,
        "category": WeaponCategory.SPEAR,
        "tier": 0,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 0.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(damage=2.0),
    },
    GreenskinsWeaponId.BONE_PICK_00.value: {
        "id": GreenskinsWeaponId.BONE_PICK_00.value,
        "name": "Кирки из костей",
        "lore": "Бедренная кость огра, примотанная к палке сухожилиями. Копать ей тяжело, зато черепа пробивает отлично.",
        "slot": _SLOT,
        "category": WeaponCategory.AXE,
        "tier": 0,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 0.0,
        "cost_material": 0.5,
        "stats": EquipmentStats(
            damage=3.0,
            armor_piercing=2.0,
        ),
    },
    GreenskinsWeaponId.CRUDE_CHOPPA_01.value: {
        "id": GreenskinsWeaponId.CRUDE_CHOPPA_01.value,
        "name": "Грубые рубила",
        "lore": "Кусок железа, который однажды был плугом или мечом. Не режет, а ломает кости за счет веса.",
        "slot": _SLOT,
        "category": WeaponCategory.AXE,
        "tier": 1,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 0.5,
        "cost_material": 1.0,
        "stats": EquipmentStats(damage=6.0),
    },
    GreenskinsWeaponId.CROOKED_SPEAR_01.value: {
        "id": GreenskinsWeaponId.CROOKED_SPEAR_01.value,
        "name": "Кривые копья",
        "lore": "Ржавые наконечники на кривых древках. Удобно бить из второго ряда.",
        "slot": _SLOT,
        "category": WeaponCategory.SPEAR,
        "tier": 1,
        "tags": {EquipmentTag.TWO_HANDED},
        "cost_gold": 0.5,
        "cost_material": 1.5,
        "stats": EquipmentStats(
            damage=5.0,
            range_hexes=2,
        ),
    },
    GreenskinsWeaponId.TWO_HANDED_HAMMER_02.value: {
        "id": GreenskinsWeaponId.TWO_HANDED_HAMMER_02.value,
        "name": "Двуручная кувалда",
        "lore": "Сколочена из наковальни и бревна. Требует недюжинной силы, превращает имперских солдат в лепешки.",
        "slot": _SLOT,
        "category": WeaponCategory.AXE,  # Дробящее
        "tier": 2,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.HEAVY, EquipmentTag.SHIELD_BREAKER},
        "cost_gold": 1.0,
        "cost_material": 4.0,
        "stats": EquipmentStats(
            damage=14.0,
            armor_piercing=5.0,
            initiative_modifier=-3,
            stamina_drain_per_turn=2.0,
        ),
    },
    GreenskinsWeaponId.TOOTHED_SWORD_02.value: {
        "id": GreenskinsWeaponId.TOOTHED_SWORD_02.value,
        "name": "Зубастый меч",
        "lore": "Орочий клинковый инструмент. Края специально искорежены и зазубрены, чтобы лезвие цеплялось за броню и рвало плоть.",
        "slot": _SLOT,
        "category": WeaponCategory.GREATSWORD,
        "tier": 2,
        "tags": {EquipmentTag.TWO_HANDED},
        "cost_gold": 2.0,
        "cost_material": 3.0,
        "stats": EquipmentStats(
            damage=12.0,
            armor_piercing=8.0,
        ),
        "special_rules": "Вскрытие банок: при ударе игнорирует половину брони цели (реализовано через высокий показатель armor_piercing).",
    },
    GreenskinsWeaponId.CANNONBALL_FLAIL_02.value: {
        "id": GreenskinsWeaponId.CANNONBALL_FLAIL_02.value,
        "name": "Цеп с ядром",
        "lore": "Настоящее пушечное ядро, приваренное к цепи. Управлять им невозможно, главное — раскрутить и бросить в сторону врага.",
        "slot": _SLOT,
        "category": WeaponCategory.WHIP,
        "tier": 2,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.HEAVY, EquipmentTag.SHIELD_BREAKER},
        "cost_gold": 3.0,
        "cost_material": 5.0,
        "stats": EquipmentStats(
            damage=16.0,
            initiative_modifier=-4,
            stamina_drain_per_turn=2.5,
        ),
        "special_rules": "Опасный замах: наносит огромный урон по площади, но имеет 10% шанс нанести урон соседнему союзному отряду (или самому себе) при промахе.",
    },
    GreenskinsWeaponId.SHAMAN_STAFF_03.value: {
        "id": GreenskinsWeaponId.SHAMAN_STAFF_03.value,
        "name": "Шаманский посох с черепом",
        "lore": "Кривая палка, увенчанная фонящим от магии черепом. Шаман чаще бьет им по головам своих же гоблинов, чем колдует.",
        "slot": _SLOT,
        "category": WeaponCategory.MAGIC,
        "tier": 3,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 5.0,
        "cost_material": 8.0,
        "stats": EquipmentStats(
            damage=10.0,
            armor_piercing=10.0,  # Магический урон пробивает сталь
        ),
    },
    GreenskinsWeaponId.UPROOTED_TREE_04.value: {
        "id": GreenskinsWeaponId.UPROOTED_TREE_04.value,
        "name": "Вырванное дерево",
        "lore": "Огру не нужно кузнечное дело. Он просто вырывает сосну с корнем и идет ломать стены.",
        "slot": _SLOT,
        "category": WeaponCategory.POLEARM,
        "tier": 4,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.HEAVY, EquipmentTag.SHIELD_BREAKER},
        "cost_gold": 0.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(
            damage=30.0,
            range_hexes=2,
            damage_bonus_vs_size={
                UnitSizeCategory.SMALL: 0.5,  # Сносит толпы мелких
                UnitSizeCategory.MEDIUM: 0.5,
            },
        ),
    },
    GreenskinsWeaponId.RUSTY_ANCHOR_04.value: {
        "id": GreenskinsWeaponId.RUSTY_ANCHOR_04.value,
        "name": "Ржавый якорь",
        "lore": "Корабельный якорь, который огр использует как двуручный топор. Острие легко вскрывает замковые ворота.",
        "slot": _SLOT,
        "category": WeaponCategory.AXE,
        "tier": 4,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.HEAVY},
        "cost_gold": 5.0,
        "cost_material": 15.0,
        "stats": EquipmentStats(
            damage=35.0,
            armor_piercing=15.0,
            initiative_modifier=-5,
        ),
    },
    GreenskinsWeaponId.METEORITE_AXE_05.value: {
        "id": GreenskinsWeaponId.METEORITE_AXE_05.value,
        "name": "Секира из метеорита",
        "lore": "Кусок Прародителя, грубо вбитый в стальное древко. Оружие невероятной тяжести, излучающее смертельную магию.",
        "slot": _SLOT,
        "category": WeaponCategory.AXE,
        "tier": 5,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.RESONITE_POWERED, EquipmentTag.HEAVY},
        "cost_gold": 20.0,
        "cost_material": 25.0,
        "stats": EquipmentStats(
            damage=40.0,
            armor_piercing=20.0,
        ),
        "special_rules": "Жажда битвы: при убийстве вражеского отряда восстанавливает часть выносливости своему носителю.",
    },
}
