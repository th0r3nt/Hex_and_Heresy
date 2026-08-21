"""
Реестр брони фракции 'Паства метеорита'.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    ArmorCategory,
    EquipmentSlot,
    EquipmentTag,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.congregation_of_the_meteorite.common import CotmArmorId

_SLOT = EquipmentSlot.ARMOR

ARMOR_LIST: dict[str, dict[str, Any]] = {
    CotmArmorId.CULTIST_RAGS_00.value: {
        "id": CotmArmorId.CULTIST_RAGS_00.value,
        "name": "Рубища сектантов",
        "lore": "Грязные, пропитанные кровью и потом балахоны. Не дают никакой защиты.",
        "slot": _SLOT,
        "category": ArmorCategory.CLOTH,
        "tier": 0,
        "cost_gold": 0.0,
        "cost_material": 0.5,
        "stats": EquipmentStats(armor_bonus=0.0),
    },
    CotmArmorId.FLAYED_SKIN_00.value: {
        "id": CotmArmorId.FLAYED_SKIN_00.value,
        "name": "Кожа, содранная с врагов",
        "lore": "Ужасающий вид этой брони деморализует противника больше, чем защищает самого культиста.",
        "slot": _SLOT,
        "category": ArmorCategory.LEATHER,
        "tier": 0,
        "cost_gold": 0.0,
        "cost_material": 1.0,
        "stats": EquipmentStats(armor_bonus=0.5),
        "special_rules": "аура ужаса: слегка снижает мораль противников, находящихся в ближнем бою.",
    },
    CotmArmorId.RUSTY_MAIL_01.value: {
        "id": CotmArmorId.RUSTY_MAIL_01.value,
        "name": "Ржавые кольчуги",
        "lore": "Сняты с мертвецов после давних битв. Кольца давно поржавели и легко крошатся.",
        "slot": _SLOT,
        "category": ArmorCategory.MAIL,
        "tier": 1,
        "cost_gold": 1.0,
        "cost_material": 2.0,
        "stats": EquipmentStats(armor_bonus=2.5),
    },
    CotmArmorId.FUSED_FLESH_01.value: {
        "id": CotmArmorId.FUSED_FLESH_01.value,
        "name": "Сплавленная плоть",
        "lore": "Броня из сшитых и сросшихся кусков чужого мяса. Врожденная защита зомби и мутантов.",
        "slot": _SLOT,
        "category": ArmorCategory.UNARMORED,
        "tier": 1,
        "tags": {EquipmentTag.CURSED},
        "cost_gold": 0.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(armor_bonus=3.0, speed_modifier=-0.1),
    },
    CotmArmorId.GLADIATOR_CARAPACE_02.value: {
        "id": CotmArmorId.GLADIATOR_CARAPACE_02.value,
        "name": "Панцири гладиаторов",
        "lore": "Закрывают только жизненно важные органы, оставляя руки и ноги свободными для кровавой рубки.",
        "slot": _SLOT,
        "category": ArmorCategory.BRIGANDINE,
        "tier": 2,
        "cost_gold": 2.0,
        "cost_material": 4.0,
        "stats": EquipmentStats(armor_bonus=4.0),  # Без штрафов к скорости
    },
    CotmArmorId.CURSED_PLATE_02.value: {
        "id": CotmArmorId.CURSED_PLATE_02.value,
        "name": "Проклятые латы",
        "lore": "Тяжелая броня Темных латников. Она защищает носителя, но медленно выпивает его жизненные силы.",
        "slot": _SLOT,
        "category": ArmorCategory.PLATE,
        "tier": 2,
        "tags": {EquipmentTag.HEAVY, EquipmentTag.CURSED},
        "cost_gold": 4.0,
        "cost_material": 6.0,
        "stats": EquipmentStats(
            armor_bonus=8.0,
            speed_modifier=-0.1,
        ),
        "special_rules": "жажда крови: высасывает 1 ХП у каждого юнита отряда каждые два такта.",
    },
    CotmArmorId.SHADOW_CLOAKS_03.value: {
        "id": CotmArmorId.SHADOW_CLOAKS_03.value,
        "name": "Теневые плащи",
        "lore": "Сотканы из мрака и магии. Размывают силуэт носителя, делая его трудной мишенью для лучников.",
        "slot": _SLOT,
        "category": ArmorCategory.CLOTH,
        "tier": 3,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 10.0,
        "cost_material": 12.0,
        "stats": EquipmentStats(armor_bonus=2.0),
        "special_rules": "покров тьмы: дает 20% шанс уклонения от любых дальнобойных атак.",
    },
    CotmArmorId.EMBALMER_SHROUD_04.value: {
        "id": CotmArmorId.EMBALMER_SHROUD_04.value,
        "name": "Пелена бальзамировщика",
        "lore": "Бинты, пропитанные алхимическими смолами и резонитом. Защищают древних мумий от тлена.",
        "slot": _SLOT,
        "category": ArmorCategory.PADDED,
        "tier": 4,
        "tags": {EquipmentTag.CURSED},
        "cost_gold": 15.0,
        "cost_material": 25.0,
        "stats": EquipmentStats(armor_bonus=10.0),
        "special_rules": "химическая защита: дает иммунитет к огню и ядам.",
    },
    CotmArmorId.ETHEREAL_ARMOR_05.value: {
        "id": CotmArmorId.ETHEREAL_ARMOR_05.value,
        "name": "Эфирный доспех",
        "lore": "Доспехи Бессмертных всадников не существуют в физическом мире, это лишь электромагнитная проекция.",
        "slot": _SLOT,
        "category": ArmorCategory.FORCE_FIELD,
        "tier": 5,
        "tags": {EquipmentTag.CURSED, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 0.0,
        "cost_material": 40.0,
        "stats": EquipmentStats(armor_bonus=0.0),
        "special_rules": "призрачная форма: снижает любой получаемый физический урон на 50%, но удваивает получаемый магический урон.",
    },
}
