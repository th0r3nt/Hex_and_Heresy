"""
Реестр оружия ближнего боя фракции людей.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    EquipmentSlot,
    EquipmentTag,
    UnitSizeCategory,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.humans.common import HumanWeaponId

_SLOT = EquipmentSlot.WEAPON

MELEE_WEAPONS: dict[str, dict[str, Any]] = {
    HumanWeaponId.BUILDER_HAMMER_00.value: {
        "id": HumanWeaponId.BUILDER_HAMMER_00.value,
        "name": "Строительные молоты",
        "lore": "Рабочий инструмент гильдий. Бьет медленно, но если попадает — оставляет в доспехах серьезные вмятины.",
        "slot": _SLOT,
        "category": WeaponCategory.AXE,  # Используем топоры/молоты как категорию дробящего одноручного
        "tier": 0,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 0.0,
        "cost_material": 1.0,
        "stats": EquipmentStats(
            damage=4.0,
            armor_piercing=3.0,
            initiative_modifier=-2,
        ),
    },
    HumanWeaponId.RUSTY_FLAIL_00.value: {
        "id": HumanWeaponId.RUSTY_FLAIL_00.value,
        "name": "Ржавые цепы с гвоздями",
        "lore": "Оружие кающихся грешников. Из-за гибкой цепи легко огибают вражеские щиты, но наносят нестабильный урон.",
        "slot": _SLOT,
        "category": WeaponCategory.WHIP,
        "tier": 0,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.SHIELD_BREAKER},
        "cost_gold": 0.0,
        "cost_material": 1.5,
        "stats": EquipmentStats(
            damage=6.0,
        ),
    },
    HumanWeaponId.INFANTRY_SPEAR_01.value: {
        "id": HumanWeaponId.INFANTRY_SPEAR_01.value,
        "name": "Пехотное копье",
        "lore": "Дешевое, длинное и надежное. Позволяет городской страже держать врага на почтительном расстоянии.",
        "slot": _SLOT,
        "category": WeaponCategory.SPEAR,
        "tier": 1,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.BRACEABLE},
        "cost_gold": 1.0,
        "cost_material": 2.0,
        "stats": EquipmentStats(
            damage=6.0,
            range_hexes=2,
        ),
    },
    HumanWeaponId.STEEL_HALBERD_02.value: {
        "id": HumanWeaponId.STEEL_HALBERD_02.value,
        "name": "Стальные алебарды",
        "lore": "Универсальное оружие регулярной армии. Крюк сбрасывает всадников, а тяжелое лезвие прорубает толстую шкуру монстров.",
        "slot": _SLOT,
        "category": WeaponCategory.POLEARM,
        "tier": 2,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.HEAVY, EquipmentTag.BRACEABLE},
        "cost_gold": 3.0,
        "cost_material": 5.0,
        "stats": EquipmentStats(
            damage=12.0,
            range_hexes=2,
            stamina_drain_per_turn=1.5,
            damage_bonus_vs_size={
                UnitSizeCategory.LARGE: 0.3,
                UnitSizeCategory.HUGE: 0.3,
            },
        ),
    },
    HumanWeaponId.SABER_02.value: {
        "id": HumanWeaponId.SABER_02.value,
        "name": "Стальные сабли",
        "lore": "Легкое рубящее оружие, идеально подходящее для конницы или дуэлянтов.",
        "slot": _SLOT,
        "category": WeaponCategory.SWORD,
        "tier": 2,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 4.0,
        "cost_material": 3.0,
        "stats": EquipmentStats(
            damage=10.0,
            initiative_modifier=1,
        ),
    },
    HumanWeaponId.FLAMBERGE_03.value: {
        "id": HumanWeaponId.FLAMBERGE_03.value,
        "name": "Двуручные фламберги",
        "lore": "Тяжелые мечи с волнистым лезвием, оставляющие страшные рваные раны. Наносят урон сразу нескольким врагам по широкой дуге.",
        "slot": _SLOT,
        "category": WeaponCategory.GREATSWORD,
        "tier": 3,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.HEAVY},
        "cost_gold": 8.0,
        "cost_material": 8.0,
        "stats": EquipmentStats(
            damage=18.0,
            armor_piercing=2.0,
            stamina_drain_per_turn=2.0,
        ),
        "special_rules": "Сплеш-урон: наносит 30% базового урона соседним с целью клеткам (при условии наличия там врагов).",
    },
    HumanWeaponId.SILVER_RAPIER_03.value: {
        "id": HumanWeaponId.SILVER_RAPIER_03.value,
        "name": "Серебряные рапиры",
        "lore": "Оружие Инквизиции. Пробивает энергетические щиты и оставляет ожоги на телах мутантов.",
        "slot": _SLOT,
        "category": WeaponCategory.SWORD,
        "tier": 3,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.SILVER},
        "cost_gold": 12.0,
        "cost_material": 5.0,
        "stats": EquipmentStats(
            damage=14.0,
            armor_piercing=4.0,
            initiative_modifier=2,
        ),
        "special_rules": "Священное серебро: наносит х1.5 урона по целям с проклятыми генами (оборотни, нежить) и игнорирует магическую броню.",
    },
    HumanWeaponId.KNIGHT_LANCE_04.value: {
        "id": HumanWeaponId.KNIGHT_LANCE_04.value,
        "name": "Рыцарские копья",
        "lore": "Длинные турнирные копья. При правильном разгоне их кинетическая мощь прошивает насквозь даже огров.",
        "slot": _SLOT,
        "category": WeaponCategory.SPEAR,
        "tier": 4,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 15.0,
        "cost_material": 10.0,
        "stats": EquipmentStats(
            damage=15.0,
        ),
        "special_rules": "Сокрушительный натиск: +150% к базовому урону во время фазы 'Натиска'. После первого столкновения копья ломаются, и отряд переходит на резервные мечи.",
    },
    HumanWeaponId.HOLY_HAMMER_04.value: {
        "id": HumanWeaponId.HOLY_HAMMER_04.value,
        "name": "Освященные боевые молоты",
        "lore": "Тяжелые кувалды, чьи ударные части выкованы из переплавленного метеоритного железа и омыты святой водой.",
        "slot": _SLOT,
        "category": WeaponCategory.AXE,
        "tier": 4,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.SILVER},
        "cost_gold": 18.0,
        "cost_material": 12.0,
        "stats": EquipmentStats(
            damage=22.0,
            armor_piercing=8.0,
        ),
        "special_rules": "Антихил: урон от этого оружия не может быть исцелен эффектами регенерации или восстановлен некромантией.",
    },
    HumanWeaponId.CARVED_GREATSWORD_05.value: {
        "id": HumanWeaponId.CARVED_GREATSWORD_05.value,
        "name": "Резной двуручник",
        "lore": "Шедевр кузнечного дела. Идеальный баланс позволяет разрубать командиров врага одним точным движением.",
        "slot": _SLOT,
        "category": WeaponCategory.GREATSWORD,
        "tier": 5,
        "tags": {EquipmentTag.TWO_HANDED},
        "cost_gold": 35.0,
        "cost_material": 20.0,
        "stats": EquipmentStats(
            damage=30.0,
            armor_piercing=10.0,
        ),
        "special_rules": "Обезглавливание: шанс 10% мгновенно нанести смертельный урон вражескому герою или полководцу, участвующему в ближнем бою с этим отрядом.",
    },
}
