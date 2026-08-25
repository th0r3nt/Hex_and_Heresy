"""
Реестр естественной защиты нейтральных существ.
"""

from typing import Any

from src.back.gamedata.neutrals.common import NeutralsArmorId
from src.back.l01_domain.army.constants import ArmorCategory, EquipmentSlot
from src.back.l01_domain.army.models.card.equipment import EquipmentStats

_SLOT = EquipmentSlot.ARMOR

ARMOR_LIST: dict[str, dict[str, Any]] = {
    NeutralsArmorId.BEAST_HIDE_01.value: {
        "id": NeutralsArmorId.BEAST_HIDE_01.value,
        "name": "Плотная шкура",
        "lore": "Шкура, огрубевшая от радиации и постоянной борьбы за выживание.",
        "slot": _SLOT,
        "category": ArmorCategory.LEATHER,
        "tier": 1,
        "cost_gold": 0.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(armor_bonus=2.0),
    },
}