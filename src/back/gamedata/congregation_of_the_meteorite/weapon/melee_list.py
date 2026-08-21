"""
Реестр оружия ближнего боя фракции 'Паства метеорита'.
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

MELEE_WEAPONS: dict[str, dict[str, Any]] = {
    CotmWeaponId.RUSTY_KNIVES_00.value: {
        "id": CotmWeaponId.RUSTY_KNIVES_00.value,
        "name": "Ржавые ножи",
        "lore": "Минимальный рубящий урон. Годятся только для того, чтобы добивать раненых и срезать кошельки.",
        "slot": _SLOT,
        "category": WeaponCategory.DAGGER,
        "tier": 0,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 0.0,
        "cost_material": 0.5,
        "stats": EquipmentStats(damage=2.0),
    },
    CotmWeaponId.RITUAL_SICKLES_00.value: {
        "id": CotmWeaponId.RITUAL_SICKLES_00.value,
        "name": "Ритуальные серпы",
        "lore": "Используются для жертвоприношений и жатвы плоти. Их изогнутые лезвия идеально подходят для перерезания горла.",
        "slot": _SLOT,
        "category": WeaponCategory.SWORD,
        "tier": 0,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 0.5,
        "cost_material": 1.0,
        "stats": EquipmentStats(damage=3.0),
        "special_rules": "Жатва: наносят на 10% больше урона, если у цели осталось меньше половины здоровья.",
    },
    CotmWeaponId.ROTTEN_CLAWS_01.value: {
        "id": CotmWeaponId.ROTTEN_CLAWS_01.value,
        "name": "Гнилые зубы и когти",
        "lore": "Врожденное оружие нежити и демонов. Не требует производства, но несет в себе заразу.",
        "slot": _SLOT,
        "category": WeaponCategory.NATURAL,
        "tier": 1,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.CURSED},
        "cost_gold": 0.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(damage=5.0),
    },
    CotmWeaponId.HOOK_CHAINS_01.value: {
        "id": CotmWeaponId.HOOK_CHAINS_01.value,
        "name": "Цепи с крюками",
        "lore": "Ржавые цепи, которыми скрепляли рабов. Теперь они служат для того, чтобы подтаскивать врагов поближе к алтарю.",
        "slot": _SLOT,
        "category": WeaponCategory.WHIP,
        "tier": 1,
        "tags": {EquipmentTag.TWO_HANDED},
        "cost_gold": 1.0,
        "cost_material": 3.0,
        "stats": EquipmentStats(
            damage=6.0,
            range_hexes=2,
            initiative_modifier=-2,
        ),
        "special_rules": "Подтягивание: шанс 20% подтянуть вражеский отряд к себе, сломав его строй и лишив бонусов обороны.",
    },
    CotmWeaponId.CORRUPTED_FALCHIONS_02.value: {
        "id": CotmWeaponId.CORRUPTED_FALCHIONS_02.value,
        "name": "Оскверненные фальшионы",
        "lore": "Оружие Темных латников. Лезвия покрыты гнилью и черной магией.",
        "slot": _SLOT,
        "category": WeaponCategory.SWORD,
        "tier": 2,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.CURSED},
        "cost_gold": 4.0,
        "cost_material": 5.0,
        "stats": EquipmentStats(damage=11.0, armor_piercing=2.0),
        "special_rules": "Инфекция: накладывает на врага эффект, запрещающий лечение или воскрешение отряда на 2 такта.",
    },
    CotmWeaponId.REAPER_SCYTHES_02.value: {
        "id": CotmWeaponId.REAPER_SCYTHES_02.value,
        "name": "Косы жнецов",
        "lore": "Сельскохозяйственные косы, перекованные для кровавой жатвы. Идеальны для уничтожения толп ополченцев.",
        "slot": _SLOT,
        "category": WeaponCategory.POLEARM,
        "tier": 2,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.HEAVY},
        "cost_gold": 3.0,
        "cost_material": 6.0,
        "stats": EquipmentStats(
            damage=14.0,
            stamina_drain_per_turn=2.0,
        ),
        "special_rules": "Широкий размах: наносит сплеш-урон сразу трем соседним гексам перед собой.",
    },
    CotmWeaponId.RESONITE_DAGGERS_03.value: {
        "id": CotmWeaponId.RESONITE_DAGGERS_03.value,
        "name": "Кинжалы из резонита",
        "lore": "Оружие эльфийских кровопускателей. Тончайшие лезвия, проходящие сквозь сталь, как сквозь масло.",
        "slot": _SLOT,
        "category": WeaponCategory.DAGGER,
        "tier": 3,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 10.0,
        "cost_material": 15.0,
        "stats": EquipmentStats(
            damage=15.0,
            armor_piercing=20.0,  # Игнорируют практически любую броню
            initiative_modifier=3,
        ),
    },
    CotmWeaponId.SPIKED_WHIPS_03.value: {
        "id": CotmWeaponId.SPIKED_WHIPS_03.value,
        "name": "Шипованные плети",
        "lore": "Кожаные бичи с вплетенными осколками стекла и костей. Сдирают плоть с костей, оставляя незаживающие раны.",
        "slot": _SLOT,
        "category": WeaponCategory.WHIP,
        "tier": 3,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.CURSED},
        "cost_gold": 8.0,
        "cost_material": 10.0,
        "stats": EquipmentStats(
            damage=12.0,
            range_hexes=2,
        ),
        "special_rules": "Рваные раны: накладывают кровотечение, наносящее урон в течение времени.",
    },
    CotmWeaponId.GHOST_SPEARS_05.value: {
        "id": CotmWeaponId.GHOST_SPEARS_05.value,
        "name": "Призрачные копья",
        "lore": "Оружие Бессмертных всадников. Полупрозрачные лезвия, пронзающие душу в обход физической оболочки.",
        "slot": _SLOT,
        "category": WeaponCategory.SPEAR,
        "tier": 5,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.CURSED, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 0.0,
        "cost_material": 25.0,
        "stats": EquipmentStats(
            damage=25.0,
            armor_piercing=100.0,  # Считается магическим уроном
        ),
        "special_rules": "Призрачный натиск: урон от натиска умножается на x3 вместо стандартных x1.5.",
    },
}
