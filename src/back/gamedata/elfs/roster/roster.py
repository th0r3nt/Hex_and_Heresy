"""
Реестр сборки армий (Ростер) фракции эльфов.
Эльфы требуют колоссального количества материалов (резонита) и золота на найм, но провизию почти не потребляют.
"""

from typing import Any

from src.back.gamedata.elfs.common import (
    ElfsAccessoryId,
    ElfsArmorId,
    ElfsRosterId,
    ElfsUnitId,
    ElfsWeaponId,
)

_FACTION = "elfs"

ROSTER_LIST: dict[str, dict[str, Any]] = {
    ElfsRosterId.ROSTER_DISCIPLES.value: {
        "id": ElfsRosterId.ROSTER_DISCIPLES.value,
        "faction_id": _FACTION,
        "unit_archetype_id": ElfsUnitId.TEMPLE_DISCIPLES_00.value,
        "weapon_id": ElfsWeaponId.IRONWOOD_STAFF_00.value,
        "armor_id": ElfsArmorId.GHOST_SILK_ROBES_00.value,
        "accessory_id": None,
        "cost_gold": 5.0,
        "cost_material": 10.0,
    },
    ElfsRosterId.ROSTER_SEEKERS.value: {
        "id": ElfsRosterId.ROSTER_SEEKERS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": ElfsUnitId.WASTELAND_SEEKERS_00.value,
        "weapon_id": ElfsWeaponId.CRYSTAL_DAGGERS_00.value,
        "armor_id": ElfsArmorId.GHOST_SILK_ROBES_00.value,
        "accessory_id": ElfsAccessoryId.FORESIGHT_LENSES_00.value,
        "cost_gold": 8.0,
        "cost_material": 15.0,
    },
    ElfsRosterId.ROSTER_GUARDS.value: {
        "id": ElfsRosterId.ROSTER_GUARDS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": ElfsUnitId.ITHILIEN_GUARDS_01.value,
        "weapon_id": ElfsWeaponId.PURE_CLEAVE_GLAIVES_01.value,
        "armor_id": ElfsArmorId.SINGING_RESIN_ARMOR_01.value,
        "accessory_id": ElfsAccessoryId.FACELESS_MASKS_01.value,
        "cost_gold": 25.0,
        "cost_material": 35.0,  # Материалы у эльфов - это резонит. Он дорогой.
    },
    ElfsRosterId.ROSTER_ARCHERS.value: {
        "id": ElfsRosterId.ROSTER_ARCHERS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": ElfsUnitId.ITHILIEN_ARCHERS_01.value,
        "weapon_id": ElfsWeaponId.EMERALD_BOWS_01.value,
        "armor_id": ElfsArmorId.SINGING_RESIN_ARMOR_01.value,
        "accessory_id": ElfsAccessoryId.FACELESS_MASKS_01.value,
        "cost_gold": 30.0,
        "cost_material": 30.0,
    },
    ElfsRosterId.ROSTER_BLADE_DANCERS.value: {
        "id": ElfsRosterId.ROSTER_BLADE_DANCERS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": ElfsUnitId.BLADE_DANCERS_02.value,
        "weapon_id": ElfsWeaponId.TWIN_MOONBLADES_02.value,
        "armor_id": ElfsArmorId.EMERALD_WYVERN_SCALES_02.value,
        "accessory_id": ElfsAccessoryId.MIRAGE_PRISM_02.value,
        "cost_gold": 45.0,
        "cost_material": 60.0,
    },
    ElfsRosterId.ROSTER_PRIESTS.value: {
        "id": ElfsRosterId.ROSTER_PRIESTS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": ElfsUnitId.RESONITE_PRIESTS_02.value,
        "weapon_id": ElfsWeaponId.FOCUSING_SPHERES_02.value,
        "armor_id": ElfsArmorId.REFRACTION_MANTLES_03.value,
        "accessory_id": ElfsAccessoryId.ACCUMULATOR_MIRRORS_03.value,
        "cost_gold": 50.0,
        "cost_material": 80.0,
    },
    ElfsRosterId.ROSTER_BOW_MASTERS.value: {
        "id": ElfsRosterId.ROSTER_BOW_MASTERS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": ElfsUnitId.KRON_KERN_MASTERS_03.value,
        "weapon_id": ElfsWeaponId.KRON_KERN_GREATBOWS_03.value,
        "armor_id": ElfsArmorId.REFRACTION_MANTLES_03.value,
        "accessory_id": ElfsAccessoryId.RESONANT_TUNING_FORK_03.value,
        "cost_gold": 75.0,
        "cost_material": 100.0,
    },
    ElfsRosterId.ROSTER_ILLUSIONISTS.value: {
        "id": ElfsRosterId.ROSTER_ILLUSIONISTS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": ElfsUnitId.ILLUSIONIST_MAGES_03.value,
        "weapon_id": ElfsWeaponId.FOCUSING_SPHERES_02.value,  # Используют то же оружие
        "armor_id": ElfsArmorId.REFRACTION_MANTLES_03.value,
        "accessory_id": ElfsAccessoryId.MIRAGE_PRISM_02.value,
        "cost_gold": 60.0,
        "cost_material": 90.0,
    },
    ElfsRosterId.ROSTER_SENTINELS.value: {
        "id": ElfsRosterId.ROSTER_SENTINELS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": ElfsUnitId.CRYSTAL_SENTINELS_03.value,
        "weapon_id": ElfsWeaponId.PURE_CLEAVE_GLAIVES_01.value,
        "armor_id": ElfsArmorId.SYMBIOTIC_CARAPACE_03.value,
        "accessory_id": None,
        "cost_gold": 80.0,
        "cost_material": 120.0,
    },
    ElfsRosterId.ROSTER_ARK.value: {
        "id": ElfsRosterId.ROSTER_ARK.value,
        "faction_id": _FACTION,
        "unit_archetype_id": ElfsUnitId.GHOST_ARK_04.value,
        "weapon_id": ElfsWeaponId.DISTORTION_CANNONS_04.value,
        "armor_id": ElfsArmorId.ARK_ENERGY_SHIELDS_04.value,
        "accessory_id": ElfsAccessoryId.RESONATING_STONE_04.value,
        "cost_gold": 150.0,
        "cost_material": 300.0,
    },
    ElfsRosterId.ROSTER_DRAGON_LORDS.value: {
        "id": ElfsRosterId.ROSTER_DRAGON_LORDS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": ElfsUnitId.EMERALD_DRAGON_LORDS_05.value,
        "weapon_id": ElfsWeaponId.TOXIC_GLANDS_05.value,
        "armor_id": ElfsArmorId.ANTIGRAVITY_PLATE_05.value,
        "accessory_id": ElfsAccessoryId.DEW_OF_THE_PROGENITOR_05.value,
        "cost_gold": 250.0,
        "cost_material": 400.0,
    },
    ElfsRosterId.ROSTER_CELESTIAL.value: {
        "id": ElfsRosterId.ROSTER_CELESTIAL.value,
        "faction_id": _FACTION,
        "unit_archetype_id": ElfsUnitId.CELESTIAL_COMMANDER_06.value,
        "weapon_id": ElfsWeaponId.SUPERNOVA_SPEAR_06.value,
        "armor_id": ElfsArmorId.SHROUD_OF_THE_ABSOLUTE_06.value,
        "accessory_id": ElfsAccessoryId.GRAVITY_COLLAPSAR_06.value,
        "cost_gold": 1000.0,
        "cost_material": 1500.0,
    },
}
