"""
Реестр оружия ближнего боя нейтральных существ.
"""

from typing import Any

from src.back.gamedata.neutrals.common import NeutralsWeaponId
from src.back.l01_domain.army.constants import EquipmentSlot, EquipmentTag, WeaponCategory
from src.back.l01_domain.army.models.card.equipment import EquipmentStats

_SLOT = EquipmentSlot.WEAPON

MELEE_WEAPONS: dict[str, dict[str, Any]] = {
    NeutralsWeaponId.BEAST_FANGS_01.value: {
        "id": NeutralsWeaponId.BEAST_FANGS_01.value,
        "name": "Клыки и когти",
        "lore": "Врожденное оружие одичавших хищников пустошей.",
        "slot": _SLOT,
        "category": WeaponCategory.NATURAL,
        "tier": 1,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 0.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(damage=8.0, initiative_modifier=2),
    },
}