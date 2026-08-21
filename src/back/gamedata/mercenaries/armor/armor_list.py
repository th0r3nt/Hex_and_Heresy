"""
Реестр брони фракции наемников.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    ArmorCategory,
    EquipmentSlot,
    EquipmentTag,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.mercenaries.common import MercenaryArmorId

_SLOT = EquipmentSlot.ARMOR

ARMOR_LIST: dict[str, dict[str, Any]] = {
    MercenaryArmorId.COMPANY_BRIGANDINE_01.value: {
        "id": MercenaryArmorId.COMPANY_BRIGANDINE_01.value,
        "name": "Бригантины свободной роты",
        "lore": "Добротная имперская броня, с которой тщательно содраны знаки отличия. Удобная и не стесняет движений при бегстве.",
        "slot": _SLOT,
        "category": ArmorCategory.BRIGANDINE,
        "tier": 1,
        "cost_gold": 3.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(
            armor_bonus=4.0,
            speed_modifier=0.05,  # Смазанные суставы
        ),
    },
    MercenaryArmorId.BEAR_BARDING_01.value: {
        "id": MercenaryArmorId.BEAR_BARDING_01.value,
        "name": "Медвежья броня",
        "lore": "Специальные стальные листы, приклепанные к кожаной сбруе. Делает огромного зверя похожим на мохнатый танк.",
        "slot": _SLOT,
        "category": ArmorCategory.PLATE,
        "tier": 1,
        "tags": {EquipmentTag.HEAVY},
        "cost_gold": 5.0,
        "cost_material": 10.0,
        "stats": EquipmentStats(armor_bonus=8.0),
    },
    MercenaryArmorId.ADVENTURER_GEAR_02.value: {
        "id": MercenaryArmorId.ADVENTURER_GEAR_02.value,
        "name": "Снаряжение искателей приключений",
        "lore": "Смесь из эльфийских плащей, гномьей кольчуги и магических щитов. Защищает лучше, чем крепостная стена.",
        "slot": _SLOT,
        "category": ArmorCategory.MAIL,
        "tier": 2,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 0.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(armor_bonus=15.0),
        "special_rules": "Плотный строй: группа из 4-х героев получает бонус к уклонению.",
    },
    MercenaryArmorId.ZEPPELIN_HULL_03.value: {
        "id": MercenaryArmorId.ZEPPELIN_HULL_03.value,
        "name": "Корпус дирижабля",
        "lore": "Обшивка из пропитанной смолой парусины и стальных каркасов. Висит высоко в небе, недосягаемый для большинства атак.",
        "slot": _SLOT,
        "category": ArmorCategory.CARAPACE,
        "tier": 3,
        "tags": {EquipmentTag.HEAVY},
        "cost_gold": 20.0,
        "cost_material": 30.0,
        "stats": EquipmentStats(
            armor_bonus=10.0,
            speed_modifier=0.2,  # Летает
        ),
        "special_rules": "Воздушное превосходство: дирижабль левитирует. Его невозможно атаковать в ближнем бою пехотой или кавалерией. Уязвим только для стрелков и магии.",
    },
}
