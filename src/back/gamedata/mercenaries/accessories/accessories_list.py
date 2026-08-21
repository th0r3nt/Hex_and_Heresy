"""
Реестр аксессуаров фракции наемников.
Включает уникальные механики трусости и потери контроля над животными.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    AccessoryCategory,
    EquipmentSlot,
    EquipmentTag,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.mercenaries.common import MercenaryAccessoryId

_SLOT = EquipmentSlot.ACCESSORY

ACCESSORIES_LIST: dict[str, dict[str, Any]] = {
    MercenaryAccessoryId.ADVANCE_PAYMENT_01.value: {
        "id": MercenaryAccessoryId.ADVANCE_PAYMENT_01.value,
        "name": "Мешочек с авансом",
        "lore": "Мы стреляем за золото, а не за королей. Отряд воодушевлен звонкой монетой, но умирать за нее не планирует.",
        "slot": _SLOT,
        "category": AccessoryCategory.MISC,
        "tier": 1,
        "cost_gold": 5.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(initiative_modifier=1),
        "special_rules": "Трусость наемника: отряд имеет отличную мораль, но если их здоровье падает ниже 20%, они автоматически сбегают с поля боя, прихватив аванс.",
    },
    MercenaryAccessoryId.TAMER_WHIP_01.value: {
        "id": MercenaryAccessoryId.TAMER_WHIP_01.value,
        "name": "Кнут укротителя",
        "lore": "Длинная кожаная плеть для направления ярости боевых медведей.",
        "slot": _SLOT,
        "category": AccessoryCategory.INSTRUMENT,
        "tier": 1,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 2.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(),
        "special_rules": "Потеря контроля: если у нанимателя кончается провизия или укротители убиты, медведи впадают в бешенство и начинают атаковать ближайшие отряды (даже союзные).",
    },
    MercenaryAccessoryId.QUEST_ARTIFACT_02.value: {
        "id": MercenaryAccessoryId.QUEST_ARTIFACT_02.value,
        "name": "Квестовый артефакт",
        "lore": "Герои по найму требуют не только золота, но и артефактов для 'выполнения квеста'.",
        "slot": _SLOT,
        "category": AccessoryCategory.RELIC,
        "tier": 2,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 0.0,
        "cost_material": 10.0,
        "stats": EquipmentStats(),
        "special_rules": "Сила сюжета: отряд героев периодически кричит нелепые фразы, получая временные бонусы к урону.",
    },
    MercenaryAccessoryId.BOMBSIGHT_03.value: {
        "id": MercenaryAccessoryId.BOMBSIGHT_03.value,
        "name": "Аэронавигационный прицел",
        "lore": "Инженерное устройство капитана Вэнса. Позволяет гоблинам более-менее точно скидывать бомбы с высоты.",
        "slot": _SLOT,
        "category": AccessoryCategory.MISC,
        "tier": 3,
        "cost_gold": 10.0,
        "cost_material": 15.0,
        "stats": EquipmentStats(initiative_modifier=2),
    },
}
