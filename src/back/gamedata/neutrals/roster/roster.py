"""
Реестр готовых рецептов найма и спавна нейтральных сил.
Активно переиспользует экипировку других фракций.
"""

from typing import Any

from src.back.gamedata.baronial_troops.common import BaronialArmorId, BaronialWeaponId
from src.back.gamedata.humans.common import HumanArmorId, HumanWeaponId
from src.back.gamedata.neutrals.common import (
    NeutralsArmorId,
    NeutralsRosterId,
    NeutralsUnitId,
    NeutralsWeaponId,
)

_FACTION = "neutrals"

ROSTER_LIST: dict[str, dict[str, Any]] = {
    NeutralsRosterId.ROSTER_REBELS.value: {
        "id": NeutralsRosterId.ROSTER_REBELS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": NeutralsUnitId.REBELS_MOB_00.value,
        "weapon_id": BaronialWeaponId.RUSTY_PITCHFORK_00.value,
        "armor_id": BaronialArmorId.TORN_CAFTANS_00.value,
        "accessory_id": None,
        "cost_gold": 1.0,
        "cost_material": 2.0,
    },
    NeutralsRosterId.ROSTER_MARAUDERS.value: {
        "id": NeutralsRosterId.ROSTER_MARAUDERS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": NeutralsUnitId.MARAUDERS_01.value,
        "weapon_id": BaronialWeaponId.CARPENTER_AXE_00.value,
        "armor_id": HumanArmorId.PADDED_JACKETS_01.value,
        "accessory_id": None,
        "cost_gold": 4.0,
        "cost_material": 4.0,
    },
    NeutralsRosterId.ROSTER_BEASTS.value: {
        "id": NeutralsRosterId.ROSTER_BEASTS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": NeutralsUnitId.WILD_BEASTS_01.value,
        "weapon_id": NeutralsWeaponId.BEAST_FANGS_01.value,
        "armor_id": NeutralsArmorId.BEAST_HIDE_01.value,
        "accessory_id": None,
        "cost_gold": 0.0,
        "cost_material": 0.0,
    },
    NeutralsRosterId.ROSTER_DESERTERS.value: {
        "id": NeutralsRosterId.ROSTER_DESERTERS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": NeutralsUnitId.DESERTER_GANG_02.value,
        "weapon_id": HumanWeaponId.STEEL_HALBERD_02.value,
        "armor_id": HumanArmorId.STEEL_CUIRASSES_02.value,
        "accessory_id": None,
        "cost_gold": 20.0,
        "cost_material": 15.0,
    },
}