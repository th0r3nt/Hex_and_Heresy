"""
Перечисления идентификаторов (ID) для снаряжения, архетипов, рецептов и зданий фракции зеленокожих.
"""

from enum import Enum

class GreenskinsWeaponId(str, Enum):
    """Идентификаторы оружия зеленокожих."""
    
    # Ближний бой
    SHARPENED_STICK_00 = "wpn_grn_sharpened_stick_00"
    BONE_PICK_00 = "wpn_grn_bone_pick_00"
    CRUDE_CHOPPA_01 = "wpn_grn_crude_choppa_01"
    CROOKED_SPEAR_01 = "wpn_grn_crooked_spear_01"
    TWO_HANDED_HAMMER_02 = "wpn_grn_two_handed_hammer_02"
    TOOTHED_SWORD_02 = "wpn_grn_toothed_sword_02"
    CANNONBALL_FLAIL_02 = "wpn_grn_cannonball_flail_02"
    SHAMAN_STAFF_03 = "wpn_grn_shaman_staff_03"
    UPROOTED_TREE_04 = "wpn_grn_uprooted_tree_04"
    RUSTY_ANCHOR_04 = "wpn_grn_rusty_anchor_04"
    GIANT_CLUB_04 = "wpn_grn_giant_club_04"
    METEORITE_AXE_05 = "wpn_grn_meteorite_axe_05"

    # Дальний бой
    DART_BUNDLE_01 = "wpn_grn_dart_bundle_01"
    STOLEN_BOMBS_03 = "wpn_grn_stolen_bombs_03"
    STOLEN_MUSKET_03 = "wpn_grn_stolen_musket_03"


class GreenskinsArmorId(str, Enum):
    """Идентификаторы брони зеленокожих."""
    BARE_TORSO_00 = "arm_grn_bare_torso_00"
    DOG_SKIN_LOINCLOTH_00 = "arm_grn_dog_skin_loincloth_00"
    BOILED_LEATHER_01 = "arm_grn_boiled_leather_01"
    STRAW_SACKS_01 = "arm_grn_straw_sacks_01"
    SCRAP_METAL_GUARDS_02 = "arm_grn_scrap_metal_guards_02"
    CHAINED_MAIL_02 = "arm_grn_chained_mail_02"
    SANDBAGS_WITH_NAILS_02 = "arm_grn_sandbags_with_nails_02"
    STOLEN_KNIGHT_PLATE_03 = "arm_grn_stolen_knight_plate_03"
    RITUAL_TATTOOS_03 = "arm_grn_ritual_tattoos_03"
    CAULDRON_ARMOR_04 = "arm_grn_cauldron_armor_04"
    BLACK_IRON_ARMOR_05 = "arm_grn_black_iron_armor_05"


class GreenskinsAccessoryId(str, Enum):
    """Идентификаторы аксессуаров зеленокожих."""
    NAILED_PLANK_00 = "acc_grn_nailed_plank_00"
    ROTTEN_MUSHROOMS_00 = "acc_grn_rotten_mushrooms_00"
    STOLEN_TOWER_SHIELD_01 = "acc_grn_stolen_tower_shield_01"
    SCAVENGER_NET_01 = "acc_grn_scavenger_net_01"
    OFFHAND_AXE_01 = "acc_grn_offhand_axe_01"
    TRIBAL_DRUM_02 = "acc_grn_tribal_drum_02"
    RED_AMANITAS_02 = "acc_grn_red_amanitas_02"
    GLASS_SCOPE_03 = "acc_grn_glass_scope_03"
    AMULET_OF_MADNESS_03 = "acc_grn_amulet_of_madness_03"
    BUNGEE_WINCH_03 = "acc_grn_bungee_winch_03"
    BASKET_SPOTTER_04 = "acc_grn_basket_spotter_04"
    STOLEN_IMPERIAL_STANDARD_05 = "acc_grn_stolen_imperial_standard_05"
    SPORE_HEARTH_06 = "acc_grn_spore_hearth_06"


class GreenskinsUnitId(str, Enum):
    """Идентификаторы базовых архетипов юнитов зеленокожих."""
    GOBLIN_SLAVES_00 = "unit_grn_goblin_slaves_00"
    MUSHROOM_GATHERERS_00 = "unit_grn_mushroom_gatherers_00"
    YOUNG_ORCS_01 = "unit_grn_young_orcs_01"
    ORC_TRICKSTERS_01 = "unit_grn_orc_tricksters_01"
    HARDENED_ORCS_02 = "unit_grn_hardened_orcs_02"
    SHAMAN_APPRENTICES_02 = "unit_grn_shaman_apprentices_02"
    IRONJAWS_03 = "unit_grn_ironjaws_03"
    SNEAKY_GITS_03 = "unit_grn_sneaky_gits_03"
    CAVE_OGRE_04 = "unit_grn_cave_ogre_04"


class GreenskinsRosterId(str, Enum):
    """Идентификаторы готовых рецептов найма (карточек) зеленокожих."""
    ROSTER_GOBLIN_SLAVES = "rost_grn_goblin_slaves"
    ROSTER_SPEAR_THROWERS = "rost_grn_spear_throwers"
    ROSTER_BOYZ_CHOPPAS = "rost_grn_boyz_choppas"
    ROSTER_HARDENED_HAMMERS = "rost_grn_hardened_hammers"
    ROSTER_MAD_SHAMANS = "rost_grn_mad_shamans"
    ROSTER_SNIPER_BAND = "rost_grn_sniper_band"
    ROSTER_CAVE_OGRE = "rost_grn_cave_ogre"


class GreenskinsBuildingId(str, Enum):
    """Идентификаторы зданий зеленокожих."""
    CHIEFTAIN_TENT = "bld_grn_chieftain_tent"
    MUSTER_FIELD = "bld_grn_muster_field"
    MUSHROOM_CAVES = "bld_grn_mushroom_caves"
    SCRAPYARD = "bld_grn_scrapyard"
    HUCKSTER_CAMP = "bld_grn_huckster_camp"
    FIGHTING_PITS = "bld_grn_fighting_pits"
    IRONJAW_FORGE = "bld_grn_ironjaw_forge"
    OGRE_PIT = "bld_grn_ogre_pit"
    CHIEFTAIN_IDOL = "bld_grn_chieftain_idol"
    FEAR_TOTEM = "bld_grn_fear_totem"