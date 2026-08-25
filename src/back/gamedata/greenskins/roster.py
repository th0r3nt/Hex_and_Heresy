"""
Реестр сборки армий (Ростер) фракции зеленокожих.
Объединяет UnitArchetype + Weapon + Armor + Accessory в готовую карточку найма.
"""

from typing import Any

from src.back.gamedata.greenskins.common import (
    GreenskinsAccessoryId,
    GreenskinsArmorId,
    GreenskinsRosterId,
    GreenskinsUnitId,
    GreenskinsWeaponId,
)

_FACTION = "greenskins"

ROSTER_LIST: dict[str, dict[str, Any]] = {
    GreenskinsRosterId.ROSTER_GOBLIN_SLAVES.value: {
        "id": GreenskinsRosterId.ROSTER_GOBLIN_SLAVES.value,
        "faction_id": _FACTION,
        "unit_archetype_id": GreenskinsUnitId.GOBLIN_SLAVES_00.value,
        "weapon_id": GreenskinsWeaponId.BONE_PICK_00.value,
        "armor_id": GreenskinsArmorId.BARE_TORSO_00.value,
        "accessory_id": GreenskinsAccessoryId.NAILED_PLANK_00.value,
        "cost_gold": 1.0,
        "cost_material": 5.0,  # Дешево, собирается из мусора
    },
    GreenskinsRosterId.ROSTER_SPEAR_THROWERS.value: {
        "id": GreenskinsRosterId.ROSTER_SPEAR_THROWERS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": GreenskinsUnitId.MUSHROOM_GATHERERS_00.value,
        "weapon_id": GreenskinsWeaponId.CROOKED_SPEAR_01.value,
        "armor_id": GreenskinsArmorId.DOG_SKIN_LOINCLOTH_00.value,
        "accessory_id": GreenskinsAccessoryId.ROTTEN_MUSHROOMS_00.value,
        "cost_gold": 2.0,
        "cost_material": 8.0,
    },
    GreenskinsRosterId.ROSTER_BOYZ_CHOPPAS.value: {
        "id": GreenskinsRosterId.ROSTER_BOYZ_CHOPPAS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": GreenskinsUnitId.YOUNG_ORCS_01.value,
        "weapon_id": GreenskinsWeaponId.CRUDE_CHOPPA_01.value,
        "armor_id": GreenskinsArmorId.BOILED_LEATHER_01.value,
        "accessory_id": GreenskinsAccessoryId.STOLEN_TOWER_SHIELD_01.value,
        "cost_gold": 5.0,
        "cost_material": 15.0,
    },
    GreenskinsRosterId.ROSTER_HARDENED_HAMMERS.value: {
        "id": GreenskinsRosterId.ROSTER_HARDENED_HAMMERS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": GreenskinsUnitId.HARDENED_ORCS_02.value,
        "weapon_id": GreenskinsWeaponId.TWO_HANDED_HAMMER_02.value,
        "armor_id": GreenskinsArmorId.SCRAP_METAL_GUARDS_02.value,
        "accessory_id": GreenskinsAccessoryId.TRIBAL_DRUM_02.value,
        "cost_gold": 12.0,
        "cost_material": 25.0,
    },
    GreenskinsRosterId.ROSTER_MAD_SHAMANS.value: {
        "id": GreenskinsRosterId.ROSTER_MAD_SHAMANS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": GreenskinsUnitId.SHAMAN_APPRENTICES_02.value,
        "weapon_id": GreenskinsWeaponId.SHAMAN_STAFF_03.value,
        "armor_id": GreenskinsArmorId.RITUAL_TATTOOS_03.value,
        "accessory_id": GreenskinsAccessoryId.AMULET_OF_MADNESS_03.value,
        "cost_gold": 20.0,
        "cost_material": 30.0,
    },
    GreenskinsRosterId.ROSTER_SNIPER_BAND.value: {
        "id": GreenskinsRosterId.ROSTER_SNIPER_BAND.value,
        "faction_id": _FACTION,
        "unit_archetype_id": GreenskinsUnitId.SNEAKY_GITS_03.value,
        "weapon_id": GreenskinsWeaponId.STOLEN_MUSKET_03.value,
        "armor_id": GreenskinsArmorId.STRAW_SACKS_01.value,
        "accessory_id": GreenskinsAccessoryId.GLASS_SCOPE_03.value,
        "cost_gold": 30.0,  # Огнестрел ценится дорого
        "cost_material": 20.0,
    },
    GreenskinsRosterId.ROSTER_CAVE_OGRE.value: {
        "id": GreenskinsRosterId.ROSTER_CAVE_OGRE.value,
        "faction_id": _FACTION,
        "unit_archetype_id": GreenskinsUnitId.CAVE_OGRE_04.value,
        "weapon_id": GreenskinsWeaponId.UPROOTED_TREE_04.value,
        "armor_id": GreenskinsArmorId.CAULDRON_ARMOR_04.value,
        "accessory_id": GreenskinsAccessoryId.BASKET_SPOTTER_04.value,
        "cost_gold": 40.0,
        "cost_material": 80.0,  # Очень много металла уходит на котлы
    },
}
