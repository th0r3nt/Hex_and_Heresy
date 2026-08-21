"""
Реестр оружия ближнего боя фракции баронских войск.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    EquipmentSlot,
    EquipmentTag,
    UnitSizeCategory,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.baronial_troops.common import BaronialWeaponId

_SLOT = EquipmentSlot.WEAPON

MELEE_WEAPONS: dict[str, dict[str, Any]] = {
    BaronialWeaponId.RUSTY_PITCHFORK_00.value: {
        "id": BaronialWeaponId.RUSTY_PITCHFORK_00.value,
        "name": "Ржавые вилы",
        "lore": "Бьют недалеко, тупятся быстро, но для крестьянского бунта вполне сойдет.",
        "slot": _SLOT,
        "category": WeaponCategory.POLEARM,
        "tier": 0,
        "tags": {EquipmentTag.TWO_HANDED},
        "cost_gold": 0.0,
        "cost_material": 1.0,
        "stats": EquipmentStats(
            damage=3.0,
            range_hexes=2,  # Можно колоть из второго ряда
        ),
    },
    BaronialWeaponId.CARPENTER_AXE_00.value: {
        "id": BaronialWeaponId.CARPENTER_AXE_00.value,
        "name": "Плотницкие топоры",
        "lore": "Обычный рабочий инструмент. Короткая дистанция, неплохо колют старые деревянные щиты.",
        "slot": _SLOT,
        "category": WeaponCategory.AXE,
        "tier": 0,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.SHIELD_BREAKER},
        "cost_gold": 0.5,
        "cost_material": 1.0,
        "stats": EquipmentStats(damage=4.0),
    },
    BaronialWeaponId.CHEAP_HALBERD_01.value: {
        "id": BaronialWeaponId.CHEAP_HALBERD_01.value,
        "name": "Дешевые алебарды",
        "lore": "Оружие стражи, наспех скованное замковым кузнецом из переплавленного старья.",
        "slot": _SLOT,
        "category": WeaponCategory.POLEARM,
        "tier": 1,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.BRACEABLE},
        "cost_gold": 1.5,
        "cost_material": 2.0,
        "stats": EquipmentStats(
            damage=6.0,
            range_hexes=2,
        ),
    },
    BaronialWeaponId.STEEL_MORNINGSTAR_02.value: {
        "id": BaronialWeaponId.STEEL_MORNINGSTAR_02.value,
        "name": "Стальные моргенштерны",
        "lore": "Шипастые железные шары на цепях. Идеальное оружие для вскрытия имперских лат и дробления орочьих черепов.",
        "slot": _SLOT,
        "category": WeaponCategory.WHIP,  # Механически огибает щиты
        "tier": 2,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.SHIELD_BREAKER, EquipmentTag.HEAVY},
        "cost_gold": 4.0,
        "cost_material": 5.0,
        "stats": EquipmentStats(
            damage=12.0,
            armor_piercing=8.0,  # Превосходное пробитие
            initiative_modifier=-2,  # Медленный замах
            stamina_drain_per_turn=1.5,
        ),
    },
    BaronialWeaponId.MERCENARY_GREATSWORD_02.value: {
        "id": BaronialWeaponId.MERCENARY_GREATSWORD_02.value,
        "name": "Тяжелые мечи наемников",
        "lore": "Двуручные клинки со сколотыми гербами. Одинаково эффективно рубят головы и пробивают бреши в заборах.",
        "slot": _SLOT,
        "category": WeaponCategory.GREATSWORD,
        "tier": 2,
        "tags": {EquipmentTag.TWO_HANDED},
        "cost_gold": 5.0,
        "cost_material": 4.0,
        "stats": EquipmentStats(
            damage=14.0,
            armor_piercing=2.0,
        ),
    },
    BaronialWeaponId.EXECUTIONER_AXE_03.value: {
        "id": BaronialWeaponId.EXECUTIONER_AXE_03.value,
        "name": "Топор палача",
        "lore": "Огромное, бритвенно-острое лезвие на длинном древке. Одним своим видом заставляет вражеских ополченцев бросать оружие.",
        "slot": _SLOT,
        "category": WeaponCategory.AXE,
        "tier": 3,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.HEAVY},
        "cost_gold": 8.0,
        "cost_material": 6.0,
        "stats": EquipmentStats(
            damage=20.0,
            armor_piercing=5.0,
            stamina_drain_per_turn=2.0,
        ),
        "special_rules": "Запах смерти: каждая успешная атака наносит дополнительный урон морали цели.",
    },
    BaronialWeaponId.IRON_FENCE_04.value: {
        "id": BaronialWeaponId.IRON_FENCE_04.value,
        "name": "Вырванная ограда",
        "lore": "Кусок кованой железной решетки из замкового парка. Огр использует её как дубину, сминая любые щиты и кости.",
        "slot": _SLOT,
        "category": WeaponCategory.POLEARM,
        "tier": 4,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.HEAVY, EquipmentTag.SHIELD_BREAKER},
        "cost_gold": 0.0,
        "cost_material": 5.0,
        "stats": EquipmentStats(
            damage=28.0,
            armor_piercing=10.0,
            range_hexes=2,
            damage_bonus_vs_size={
                UnitSizeCategory.MEDIUM: 0.3,
            },
        ),
    },
    BaronialWeaponId.TOURNAMENT_LANCE_05.value: {
        "id": BaronialWeaponId.TOURNAMENT_LANCE_05.value,
        "name": "Имперское турнирное копье",
        "lore": "Тяжелое кавалерийское копье, украшенное выцветшими лентами. Приватизировано дезертирами. Наносимый им урон при натиске колоссален.",
        "slot": _SLOT,
        "category": WeaponCategory.SPEAR,
        "tier": 5,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 15.0,
        "cost_material": 10.0,
        "stats": EquipmentStats(
            damage=15.0,
            armor_piercing=5.0,
        ),
        "special_rules": "Рыцарский таран: урон умножается при натиске. Ломается после первого столкновения, после чего всадник переходит на меч.",
    },
}
