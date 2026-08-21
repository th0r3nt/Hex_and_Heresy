"""
Перечисления идентификаторов (ID) для снаряжения, архетипов, рецептов и зданий фракции баронских войск.
"""

from enum import Enum


class BaronialWeaponId(str, Enum):
    """Идентификаторы оружия баронств."""

    # Ближний бой
    RUSTY_PITCHFORK_00 = "wpn_bar_rusty_pitchfork_00"
    CARPENTER_AXE_00 = "wpn_bar_carpenter_axe_00"
    CHEAP_HALBERD_01 = "wpn_bar_cheap_halberd_01"
    STEEL_MORNINGSTAR_02 = "wpn_bar_steel_morningstar_02"
    MERCENARY_GREATSWORD_02 = "wpn_bar_mercenary_greatsword_02"
    EXECUTIONER_AXE_03 = "wpn_bar_executioner_axe_03"
    IRON_FENCE_04 = "wpn_bar_iron_fence_04"
    TOURNAMENT_LANCE_05 = "wpn_bar_tournament_lance_05"

    # Дальний бой
    HEAVY_CROSSBOW_01 = "wpn_bar_heavy_crossbow_01"
    LINKED_CROSSBOW_06 = "wpn_bar_linked_crossbow_06"


class BaronialArmorId(str, Enum):
    """Идентификаторы брони баронств."""

    TORN_CAFTANS_00 = "arm_bar_torn_caftans_00"
    THICK_GAMBESON_00 = "arm_bar_thick_gambeson_00"
    DENSE_PADDED_JACKETS_01 = "arm_bar_dense_padded_jackets_01"
    WORN_BRIGANDINE_02 = "arm_bar_worn_brigandine_02"
    CASTLE_HALF_PLATE_02 = "arm_bar_castle_half_plate_02"
    EXECUTIONER_APRON_03 = "arm_bar_executioner_apron_03"
    HANGING_GATES_04 = "arm_bar_hanging_gates_04"
    DESERTER_KNIGHT_PLATE_05 = "arm_bar_deserter_knight_plate_05"
    BARONIAL_CARRIAGE_ARMOR_06 = "arm_bar_baronial_carriage_armor_06"


class BaronialAccessoryId(str, Enum):
    """Идентификаторы аксессуаров баронств."""

    CHEAP_SWILL_MUG_00 = "acc_bar_cheap_swill_mug_00"
    PAVISE_SHIELD_01 = "acc_bar_pavise_shield_01"
    TORCH_AND_OIL_01 = "acc_bar_torch_and_oil_01"
    HOOKS_ON_ROPE_02 = "acc_bar_hooks_on_rope_02"
    ALE_BARREL_02 = "acc_bar_ale_barrel_02"
    PACK_OF_WOLFHOUNDS_03 = "acc_bar_pack_of_wolfhounds_03"
    BARONY_CODE_BOOK_03 = "acc_bar_barony_code_book_03"
    RAW_MEAT_LURE_04 = "acc_bar_raw_meat_lure_04"
    ENEMY_DEBT_RECEIPTS_05 = "acc_bar_enemy_debt_receipts_05"
    HOSTAGE_CAGE_06 = "acc_bar_hostage_cage_06"


class BaronialUnitId(str, Enum):
    """Идентификаторы базовых архетипов юнитов баронств."""

    SERFS_MOB_00 = "unit_bar_serfs_mob_00"
    TAX_COLLECTORS_00 = "unit_bar_tax_collectors_00"
    SIGNALMEN_00 = "unit_bar_signalmen_00"
    CASTLE_GUARDS_01 = "unit_bar_castle_guards_01"
    OUTPOST_SHOOTERS_01 = "unit_bar_outpost_shooters_01"
    VETERAN_MERCENARIES_02 = "unit_bar_veteran_mercenaries_02"
    SUPPLY_WAGON_02 = "unit_bar_supply_wagon_02"
    EXECUTIONERS_03 = "unit_bar_executioners_03"
    TAME_OGRE_04 = "unit_bar_tame_ogre_04"
    DESERTER_KNIGHTS_05 = "unit_bar_deserter_knights_05"
    BARON_CARRIAGE_06 = "unit_bar_baron_carriage_06"


class BaronialRosterId(str, Enum):
    """Идентификаторы готовых рецептов найма баронств."""

    ROSTER_SERFS = "rost_bar_serfs"
    ROSTER_TAX_COLLECTORS = "rost_bar_tax_collectors"
    ROSTER_SIGNALMEN = "rost_bar_signalmen"
    ROSTER_GUARDS = "rost_bar_guards"
    ROSTER_CROSSBOWMEN = "rost_bar_crossbowmen"
    ROSTER_MORNINGSTARS = "rost_bar_morningstars"
    ROSTER_GREATSWORDS = "rost_bar_greatswords"
    ROSTER_SUPPLY_WAGON = "rost_bar_supply_wagon"
    ROSTER_EXECUTIONERS = "rost_bar_executioners"
    ROSTER_OGRE = "rost_bar_ogre"
    ROSTER_KNIGHTS = "rost_bar_knights"
    ROSTER_CARRIAGE = "rost_bar_carriage"


class BaronialBuildingId(str, Enum):
    """Идентификаторы зданий баронств."""

    BARONS_CASTLE = "bld_bar_barons_castle"
    OPPRESSED_VILLAGE = "bld_bar_oppressed_village"
    ROADSIDE_OUTPOST = "bld_bar_roadside_outpost"
    DEBTORS_PRISON = "bld_bar_debtors_prison"
    WATCHTOWERS = "bld_bar_watchtowers"
    GARRISON_COURTYARD = "bld_bar_garrison_courtyard"
    WAGON_SHED = "bld_bar_wagon_shed"
    EXECUTION_SQUARE = "bld_bar_execution_square"
    MENAGERIE = "bld_bar_menagerie"
