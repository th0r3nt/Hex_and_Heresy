"""
Реестр сборки армий (Ростер) фракции баронских войск.
Объединяет UnitArchetype + Weapon + Armor + Accessory в готовую карточку найма.
"""

from typing import Any

from src.back.gamedata.baronial_troops.common import (
    BaronialAccessoryId,
    BaronialArmorId,
    BaronialRosterId,
    BaronialUnitId,
    BaronialWeaponId,
)

_FACTION = "baronial_troops"

ROSTER_LIST: dict[str, dict[str, Any]] = {
    BaronialRosterId.ROSTER_SERFS.value: {
        "id": BaronialRosterId.ROSTER_SERFS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": BaronialUnitId.SERFS_MOB_00.value,
        "weapon_id": BaronialWeaponId.RUSTY_PITCHFORK_00.value,
        "armor_id": BaronialArmorId.TORN_CAFTANS_00.value,
        "accessory_id": BaronialAccessoryId.CHEAP_SWILL_MUG_00.value,
        "cost_gold": 2.0,  # Очень дешево
        "cost_material": 3.0,
    },
    BaronialRosterId.ROSTER_TAX_COLLECTORS.value: {
        "id": BaronialRosterId.ROSTER_TAX_COLLECTORS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": BaronialUnitId.TAX_COLLECTORS_00.value,
        "weapon_id": BaronialWeaponId.CARPENTER_AXE_00.value,
        "armor_id": BaronialArmorId.TORN_CAFTANS_00.value,
        "accessory_id": None,
        "cost_gold": 5.0,  # Требуют аванса
        "cost_material": 2.0,
    },
    BaronialRosterId.ROSTER_SIGNALMEN.value: {
        "id": BaronialRosterId.ROSTER_SIGNALMEN.value,
        "faction_id": _FACTION,
        "unit_archetype_id": BaronialUnitId.SIGNALMEN_00.value,
        "weapon_id": BaronialWeaponId.CARPENTER_AXE_00.value,
        "armor_id": BaronialArmorId.THICK_GAMBESON_00.value,
        "accessory_id": BaronialAccessoryId.TORCH_AND_OIL_01.value,
        "cost_gold": 4.0,
        "cost_material": 4.0,
    },
    BaronialRosterId.ROSTER_GUARDS.value: {
        "id": BaronialRosterId.ROSTER_GUARDS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": BaronialUnitId.CASTLE_GUARDS_01.value,
        "weapon_id": BaronialWeaponId.CHEAP_HALBERD_01.value,
        "armor_id": BaronialArmorId.DENSE_PADDED_JACKETS_01.value,
        "accessory_id": None,
        "cost_gold": 15.0,
        "cost_material": 12.0,
    },
    BaronialRosterId.ROSTER_CROSSBOWMEN.value: {
        "id": BaronialRosterId.ROSTER_CROSSBOWMEN.value,
        "faction_id": _FACTION,
        "unit_archetype_id": BaronialUnitId.OUTPOST_SHOOTERS_01.value,
        "weapon_id": BaronialWeaponId.HEAVY_CROSSBOW_01.value,
        "armor_id": BaronialArmorId.DENSE_PADDED_JACKETS_01.value,
        "accessory_id": BaronialAccessoryId.PAVISE_SHIELD_01.value,
        "cost_gold": 20.0,
        "cost_material": 18.0,
    },
    BaronialRosterId.ROSTER_MORNINGSTARS.value: {
        "id": BaronialRosterId.ROSTER_MORNINGSTARS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": BaronialUnitId.VETERAN_MERCENARIES_02.value,
        "weapon_id": BaronialWeaponId.STEEL_MORNINGSTAR_02.value,
        "armor_id": BaronialArmorId.CASTLE_HALF_PLATE_02.value,
        "accessory_id": None,
        "cost_gold": 35.0,
        "cost_material": 25.0,
    },
    BaronialRosterId.ROSTER_GREATSWORDS.value: {
        "id": BaronialRosterId.ROSTER_GREATSWORDS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": BaronialUnitId.VETERAN_MERCENARIES_02.value,
        "weapon_id": BaronialWeaponId.MERCENARY_GREATSWORD_02.value,
        "armor_id": BaronialArmorId.WORN_BRIGANDINE_02.value,
        "accessory_id": BaronialAccessoryId.ALE_BARREL_02.value,
        "cost_gold": 30.0,
        "cost_material": 20.0,
    },
    BaronialRosterId.ROSTER_SUPPLY_WAGON.value: {
        "id": BaronialRosterId.ROSTER_SUPPLY_WAGON.value,
        "faction_id": _FACTION,
        "unit_archetype_id": BaronialUnitId.SUPPLY_WAGON_02.value,
        "weapon_id": BaronialWeaponId.CARPENTER_AXE_00.value,
        "armor_id": BaronialArmorId.WORN_BRIGANDINE_02.value,
        "accessory_id": BaronialAccessoryId.HOOKS_ON_ROPE_02.value,
        "cost_gold": 25.0,
        "cost_material": 40.0,  # Повозка требует много материалов
    },
    BaronialRosterId.ROSTER_EXECUTIONERS.value: {
        "id": BaronialRosterId.ROSTER_EXECUTIONERS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": BaronialUnitId.EXECUTIONERS_03.value,
        "weapon_id": BaronialWeaponId.EXECUTIONER_AXE_03.value,
        "armor_id": BaronialArmorId.EXECUTIONER_APRON_03.value,
        "accessory_id": BaronialAccessoryId.BARONY_CODE_BOOK_03.value,
        "cost_gold": 60.0,
        "cost_material": 30.0,
    },
    BaronialRosterId.ROSTER_OGRE.value: {
        "id": BaronialRosterId.ROSTER_OGRE.value,
        "faction_id": _FACTION,
        "unit_archetype_id": BaronialUnitId.TAME_OGRE_04.value,
        "weapon_id": BaronialWeaponId.IRON_FENCE_04.value,
        "armor_id": BaronialArmorId.HANGING_GATES_04.value,
        "accessory_id": BaronialAccessoryId.RAW_MEAT_LURE_04.value,
        "cost_gold": 80.0,
        "cost_material": 100.0,
    },
    BaronialRosterId.ROSTER_KNIGHTS.value: {
        "id": BaronialRosterId.ROSTER_KNIGHTS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": BaronialUnitId.DESERTER_KNIGHTS_05.value,
        "weapon_id": BaronialWeaponId.TOURNAMENT_LANCE_05.value,
        "armor_id": BaronialArmorId.DESERTER_KNIGHT_PLATE_05.value,
        "accessory_id": BaronialAccessoryId.ENEMY_DEBT_RECEIPTS_05.value,
        "cost_gold": 150.0,  # Очень дорогие контракты
        "cost_material": 80.0,
    },
    BaronialRosterId.ROSTER_CARRIAGE.value: {
        "id": BaronialRosterId.ROSTER_CARRIAGE.value,
        "faction_id": _FACTION,
        "unit_archetype_id": BaronialUnitId.BARON_CARRIAGE_06.value,
        "weapon_id": BaronialWeaponId.LINKED_CROSSBOW_06.value,
        "armor_id": BaronialArmorId.BARONIAL_CARRIAGE_ARMOR_06.value,
        "accessory_id": BaronialAccessoryId.HOSTAGE_CAGE_06.value,
        "cost_gold": 500.0,
        "cost_material": 600.0,
    },
}
