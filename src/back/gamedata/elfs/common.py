"""
Перечисления идентификаторов (ID) для снаряжения, архетипов, рецептов и зданий фракции эльфов.
"""

from enum import Enum


class ElfsWeaponId(str, Enum):
    """Идентификаторы оружия эльфов."""

    # Ближний бой
    IRONWOOD_STAFF_00 = "wpn_elf_ironwood_staff_00"
    CRYSTAL_DAGGERS_00 = "wpn_elf_crystal_daggers_00"
    PURE_CLEAVE_GLAIVES_01 = "wpn_elf_pure_cleave_glaives_01"
    TWIN_MOONBLADES_02 = "wpn_elf_twin_moonblades_02"
    LIQUID_LIGHT_WHIPS_03 = "wpn_elf_liquid_light_whips_03"
    SUPERNOVA_SPEAR_06 = "wpn_elf_supernova_spear_06"

    # Дальний бой
    EMERALD_BOWS_01 = "wpn_elf_emerald_bows_01"
    FOCUSING_SPHERES_02 = "wpn_elf_focusing_spheres_02"
    KRON_KERN_GREATBOWS_03 = "wpn_elf_kron_kern_greatbows_03"
    DISTORTION_CANNONS_04 = "wpn_elf_distortion_cannons_04"
    TOXIC_GLANDS_05 = "wpn_elf_toxic_glands_05"


class ElfsArmorId(str, Enum):
    """Идентификаторы брони эльфов."""

    GHOST_SILK_ROBES_00 = "arm_elf_ghost_silk_robes_00"
    SINGING_RESIN_ARMOR_01 = "arm_elf_singing_resin_armor_01"
    EMERALD_WYVERN_SCALES_02 = "arm_elf_emerald_wyvern_scales_02"
    SYMBIOTIC_CARAPACE_03 = "arm_elf_symbiotic_carapace_03"
    REFRACTION_MANTLES_03 = "arm_elf_refraction_mantles_03"
    ARK_ENERGY_SHIELDS_04 = "arm_elf_ark_energy_shields_04"
    ANTIGRAVITY_PLATE_05 = "arm_elf_antigravity_plate_05"
    SHROUD_OF_THE_ABSOLUTE_06 = "arm_elf_shroud_of_the_absolute_06"


class ElfsAccessoryId(str, Enum):
    """Идентификаторы аксессуаров эльфов."""

    FORESIGHT_LENSES_00 = "acc_elf_foresight_lenses_00"
    FACELESS_MASKS_01 = "acc_elf_faceless_masks_01"
    MIRAGE_PRISM_02 = "acc_elf_mirage_prism_02"
    ACCUMULATOR_MIRRORS_03 = "acc_elf_accumulator_mirrors_03"
    RESONANT_TUNING_FORK_03 = "acc_elf_resonant_tuning_fork_03"
    RESONATING_STONE_04 = "acc_elf_resonating_stone_04"
    DEW_OF_THE_PROGENITOR_05 = "acc_elf_dew_of_the_progenitor_05"
    GRAVITY_COLLAPSAR_06 = "acc_elf_gravity_collapsar_06"


class ElfsUnitId(str, Enum):
    """Идентификаторы базовых архетипов юнитов эльфов."""

    TEMPLE_DISCIPLES_00 = "unit_elf_temple_disciples_00"
    WASTELAND_SEEKERS_00 = "unit_elf_wasteland_seekers_00"
    ITHILIEN_GUARDS_01 = "unit_elf_ithilien_guards_01"
    ITHILIEN_ARCHERS_01 = "unit_elf_ithilien_archers_01"
    BLADE_DANCERS_02 = "unit_elf_blade_dancers_02"
    RESONITE_PRIESTS_02 = "unit_elf_resonite_priests_02"
    KRON_KERN_MASTERS_03 = "unit_elf_kron_kern_masters_03"
    ILLUSIONIST_MAGES_03 = "unit_elf_illusionist_mages_03"
    CRYSTAL_SENTINELS_03 = "unit_elf_crystal_sentinels_03"
    GHOST_ARK_04 = "unit_elf_ghost_ark_04"
    EMERALD_DRAGON_LORDS_05 = "unit_elf_emerald_dragon_lords_05"
    CELESTIAL_COMMANDER_06 = "unit_elf_celestial_commander_06"


class ElfsRosterId(str, Enum):
    """Идентификаторы готовых рецептов найма эльфов."""

    ROSTER_DISCIPLES = "rost_elf_disciples"
    ROSTER_SEEKERS = "rost_elf_seekers"
    ROSTER_GUARDS = "rost_elf_guards"
    ROSTER_ARCHERS = "rost_elf_archers"
    ROSTER_BLADE_DANCERS = "rost_elf_blade_dancers"
    ROSTER_PRIESTS = "rost_elf_priests"
    ROSTER_BOW_MASTERS = "rost_elf_bow_masters"
    ROSTER_ILLUSIONISTS = "rost_elf_illusionists"
    ROSTER_SENTINELS = "rost_elf_sentinels"
    ROSTER_ARK = "rost_elf_ark"
    ROSTER_DRAGON_LORDS = "rost_elf_dragon_lords"
    ROSTER_CELESTIAL = "rost_elf_celestial"


class ElfsBuildingId(str, Enum):
    """Идентификаторы зданий эльфов."""

    ESSENCE_EXTRACTORS = "bld_elf_essence_extractors"
    CRYSTAL_GARDENS = "bld_elf_crystal_gardens"
    SILENT_MARKET = "bld_elf_silent_market"
    SANCTUARY_OF_BLADES = "bld_elf_sanctuary_of_blades"
    SPIRE_OF_SEERS = "bld_elf_spire_of_seers"
    ASTRAL_FORGE = "bld_elf_astral_forge"
    FLOATING_SHIPYARD = "bld_elf_floating_shipyard"
    CHAMBER_OF_ECHOES = "bld_elf_chamber_of_echoes"
    MONOLITH_OF_STASIS = "bld_elf_monolith_of_stasis"
    OBSERVATORY = "bld_elf_observatory"


class ElfsLordId(str, Enum):
    """Идентификаторы легендарных владык эльфов."""

    LIANDRIS = "lord_elf_liandris"
    NAERIL = "lord_elf_naeril"
    VALORIS = "lord_elf_valoris"


class ElfsCommanderId(str, Enum):
    """Идентификаторы легендарных полководцев эльфов."""

    IRIEL = "cmd_elf_iriel"
    SILVIAN = "cmd_elf_silvian"
    KAELIN = "cmd_elf_kaelin"


class ElfsHeroId(str, Enum):
    """Идентификаторы легендарных героев эльфов."""

    ILLITHIAN = "hero_elf_illithian"
    ERINNIEL = "hero_elf_erinniel"
    FENARIL = "hero_elf_fenaril"
