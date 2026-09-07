"""
Перечисления идентификаторов (ID) для снаряжения, архетипов, рецептов и зданий фракции 'Паства метеорита'.
"""

from enum import Enum


class CotmWeaponId(str, Enum):
    """Идентификаторы оружия Паствы метеорита."""

    # Ближний бой
    RUSTY_KNIVES_00 = "wpn_cotm_rusty_knives_00"
    RITUAL_SICKLES_00 = "wpn_cotm_ritual_sickles_00"
    ROTTEN_CLAWS_01 = "wpn_cotm_rotten_claws_01"
    HOOK_CHAINS_01 = "wpn_cotm_hook_chains_01"
    CORRUPTED_FALCHIONS_02 = "wpn_cotm_corrupted_falchions_02"
    REAPER_SCYTHES_02 = "wpn_cotm_reaper_scythes_02"
    RESONITE_DAGGERS_03 = "wpn_cotm_resonite_daggers_03"
    SPIKED_WHIPS_03 = "wpn_cotm_spiked_whips_03"
    GHOST_SPEARS_05 = "wpn_cotm_ghost_spears_05"

    # Дальний бой / Магия
    NECROSIS_STAFF_04 = "wpn_cotm_necrosis_staff_04"
    PROGENITOR_FLAME_05 = "wpn_cotm_progenitor_flame_05"


class CotmArmorId(str, Enum):
    """Идентификаторы брони Паствы метеорита."""

    CULTIST_RAGS_00 = "arm_cotm_cultist_rags_00"
    FLAYED_SKIN_00 = "arm_cotm_flayed_skin_00"
    RUSTY_MAIL_01 = "arm_cotm_rusty_mail_01"
    FUSED_FLESH_01 = "arm_cotm_fused_flesh_01"
    GLADIATOR_CARAPACE_02 = "arm_cotm_gladiator_carapace_02"
    CURSED_PLATE_02 = "arm_cotm_cursed_plate_02"
    SHADOW_CLOAKS_03 = "arm_cotm_shadow_cloaks_03"
    EMBALMER_SHROUD_04 = "arm_cotm_embalmer_shroud_04"
    ETHEREAL_ARMOR_05 = "arm_cotm_ethereal_armor_05"


class CotmAccessoryId(str, Enum):
    """Идентификаторы аксессуаров Паствы метеорита."""

    BONE_AMULET_00 = "acc_cotm_bone_amulet_00"
    BLOOD_FLASK_01 = "acc_cotm_blood_flask_01"
    RUSTY_BUCKLER_01 = "acc_cotm_rusty_buckler_01"
    DARK_WHISPER_SCROLL_02 = "acc_cotm_dark_whisper_scroll_02"
    SPIKED_SHIELD_02 = "acc_cotm_spiked_shield_02"
    PROGENITOR_AMULETS_03 = "acc_cotm_progenitor_amulets_03"
    RITUAL_DAGGER_03 = "acc_cotm_ritual_dagger_03"
    CANOPIC_JAR_04 = "acc_cotm_canopic_jar_04"
    GOLDEN_IDOL_05 = "acc_cotm_golden_idol_05"


class CotmUnitId(str, Enum):
    """Идентификаторы базовых архетипов юнитов Паствы метеорита."""

    GOBLIN_LOOTERS_00 = "unit_cotm_goblin_looters_00"
    NECROMANCERS_00 = "unit_cotm_necromancers_00"
    ZOMBIE_HORDE_01 = "unit_cotm_zombie_horde_01"
    LESSER_DEMONS_01 = "unit_cotm_lesser_demons_01"
    ORC_GLADIATORS_02 = "unit_cotm_orc_gladiators_02"
    DARK_MEN_AT_ARMS_02 = "unit_cotm_dark_men_at_arms_02"
    GHOSTS_02 = "unit_cotm_ghosts_02"
    WEREWOLVES_03 = "unit_cotm_werewolves_03"
    ELF_BLOODLETTERS_03 = "unit_cotm_elf_bloodletters_03"
    BLOODLETTING_MAGE_03 = "unit_cotm_bloodletting_mage_03"
    BOMBERS_03 = "unit_cotm_bombers_03"
    MUMMY_SUMMONERS_04 = "unit_cotm_mummy_summoners_04"
    GREEDY_DRAGON_05 = "unit_cotm_greedy_dragon_05"
    IMMORTAL_RIDERS_05 = "unit_cotm_immortal_riders_05"
    DOOM_HARBINGERS_06 = "unit_cotm_doom_harbingers_06"


class CotmRosterId(str, Enum):
    """Идентификаторы готовых рецептов найма Паствы метеорита."""

    ROSTER_LOOTERS = "rost_cotm_looters"
    ROSTER_NECROMANCERS = "rost_cotm_necromancers"
    ROSTER_ZOMBIES = "rost_cotm_zombies"
    ROSTER_DEMONS = "rost_cotm_demons"
    ROSTER_GLADIATORS = "rost_cotm_gladiators"
    ROSTER_DARK_ARMS = "rost_cotm_dark_arms"
    ROSTER_GHOSTS = "rost_cotm_ghosts"
    ROSTER_WEREWOLVES = "rost_cotm_werewolves"
    ROSTER_BLOODLETTERS = "rost_cotm_bloodletters"
    ROSTER_BLOOD_MAGES = "rost_cotm_blood_mages"
    ROSTER_BOMBERS = "rost_cotm_bombers"
    ROSTER_MUMMIES = "rost_cotm_mummies"
    ROSTER_DRAGON = "rost_cotm_dragon"
    ROSTER_RIDERS = "rost_cotm_riders"
    ROSTER_HARBINGERS = "rost_cotm_harbingers"


class CotmBuildingId(str, Enum):
    """Идентификаторы зданий Паствы метеорита."""

    PROGENITOR_ALTAR = "bld_cotm_progenitor_altar"
    SECRET_SANCTUARY = "bld_cotm_secret_sanctuary"
    LOOTER_CAMP = "bld_cotm_looter_camp"
    BONE_PIT = "bld_cotm_bone_pit"
    SLAUGHTERHOUSE = "bld_cotm_slaughterhouse"
    DESECRATED_CHURCHYARD = "bld_cotm_desecrated_churchyard"
    ARENA_OF_PAIN = "bld_cotm_arena_of_pain"
    SUMMONING_CIRCLE = "bld_cotm_summoning_circle"
    TOMB_OF_THE_FORGOTTEN = "bld_cotm_tomb_of_the_forgotten"
    GATES_OF_THE_ABYSS = "bld_cotm_gates_of_the_abyss"


class CongregationLordId(str, Enum):
    """Идентификаторы легендарных иерархов Паствы метеорита."""

    MORDIUS = "lord_cotm_mordius"
    VLASTA = "lord_cotm_vlasta"
    XAPHAN = "lord_cotm_xaphan"


class CongregationCommanderId(str, Enum):
    """Идентификаторы легендарных полководцев Паствы метеорита."""

    NEKRAS = "cmd_cotm_nekras"
    VARG = "cmd_cotm_varg"
    NAMELESS_KNIGHT = "cmd_cotm_nameless_knight"


class CongregationHeroId(str, Enum):
    """Идентификаторы легендарных героев Паствы метеорита."""

    ILAI = "hero_cotm_ilai"
    MALAKAI = "hero_cotm_malakai"
