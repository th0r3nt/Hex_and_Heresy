"""
Перечисления идентификаторов (ID) для снаряжения, архетипов, рецептов и зданий фракции людей.
"""

from enum import Enum


class HumanWeaponId(str, Enum):
    BUILDER_HAMMER_00 = "wpn_hum_builder_hammer_00"
    RUSTY_FLAIL_00 = "wpn_hum_rusty_flail_00"
    INFANTRY_SPEAR_01 = "wpn_hum_infantry_spear_01"
    STEEL_HALBERD_02 = "wpn_hum_steel_halberd_02"
    SABER_02 = "wpn_hum_saber_02"
    FLAMBERGE_03 = "wpn_hum_flamberge_03"
    SILVER_RAPIER_03 = "wpn_hum_silver_rapier_03"
    KNIGHT_LANCE_04 = "wpn_hum_knight_lance_04"
    HOLY_HAMMER_04 = "wpn_hum_holy_hammer_04"
    CARVED_GREATSWORD_05 = "wpn_hum_carved_greatsword_05"
    IMPERIAL_CROSSBOW_01 = "wpn_hum_imperial_crossbow_01"
    HEAVY_ARQUEBUS_02 = "wpn_hum_heavy_arquebus_02"
    LONG_BOW_02 = "wpn_hum_long_bow_02"
    MULTI_BARREL_PISTOL_05 = "wpn_hum_multi_barrel_pistol_05"


class HumanArmorId(str, Enum):
    WORKER_ROBES_00 = "arm_hum_worker_robes_00"
    HAIRSHIRTS_00 = "arm_hum_hairshirts_00"
    PADDED_JACKETS_01 = "arm_hum_padded_jackets_01"
    LEATHER_BREASTPLATES_01 = "arm_hum_leather_breastplates_01"
    STEEL_CUIRASSES_02 = "arm_hum_steel_cuirasses_02"
    CAVALRY_MAIL_02 = "arm_hum_cavalry_mail_02"
    HEAVY_HALF_PLATE_03 = "arm_hum_heavy_half_plate_03"
    PURITY_RUNE_CLOAKS_03 = "arm_hum_purity_rune_cloaks_03"
    FULL_KNIGHT_PLATE_04 = "arm_hum_full_knight_plate_04"
    RELIQUARY_ARMOR_05 = "arm_hum_reliquary_armor_05"


class HumanAccessoryId(str, Enum):
    FLAMING_TORCHES_00 = "acc_hum_flaming_torches_00"
    PAVISE_SHIELD_01 = "acc_hum_pavise_shield_01"
    HUNTING_HORN_01 = "acc_hum_hunting_horn_01"
    POWDER_BANDOLIER_02 = "acc_hum_powder_bandolier_02"
    SURGICAL_SAWS_02 = "acc_hum_surgical_saws_02"
    HOLY_WATER_FLASK_03 = "acc_hum_holy_water_flask_03"
    STEEL_BUCKLER_03 = "acc_hum_steel_buckler_03"
    HEAVY_HERALDIC_SHIELD_04 = "acc_hum_heavy_heraldic_shield_04"
    TOMES_OF_LITANIES_04 = "acc_hum_tomes_of_litanies_04"
    MEDALLION_OF_PURITY_05 = "acc_hum_medallion_of_purity_05"


class HumanUnitId(str, Enum):
    BUILDERS_GUILD_00 = "unit_hum_builders_guild_00"
    REPENTANT_SINNERS_00 = "unit_hum_repentant_sinners_00"
    MILITIA_00 = "unit_hum_militia_00"
    CITY_GUARD_01 = "unit_hum_city_guard_01"
    HUNTERS_WITH_DOGS_01 = "unit_hum_hunters_with_dogs_01"
    IRONSIDES_02 = "unit_hum_ironsides_02"
    SHOOTERS_02 = "unit_hum_shooters_02"
    FIELD_HOSPITAL_02 = "unit_hum_field_hospital_02"
    LIGHT_CAVALRY_02 = "unit_hum_light_cavalry_02"
    WAR_VETERANS_03 = "unit_hum_war_veterans_03"
    WITCH_HUNTERS_03 = "unit_hum_witch_hunters_03"
    KNIGHTS_04 = "unit_hum_knights_04"
    INQUISITION_MAGISTERS_05 = "unit_hum_inquisition_magisters_05"
    AVATAR_OF_VENGEANCE_06 = "unit_hum_avatar_of_vengeance_06"


class HumanRosterId(str, Enum):
    ROSTER_BUILDERS = "rost_hum_builders"
    ROSTER_SINNERS = "rost_hum_sinners"
    ROSTER_MILITIA_CROSSBOWS = "rost_hum_militia_crossbows"
    ROSTER_GUARD_SPEARS = "rost_hum_guard_spears"
    ROSTER_HOUNDS = "rost_hum_hounds"
    ROSTER_IRONSIDE_HALBERDIERS = "rost_hum_ironside_halberdiers"
    ROSTER_ARQUEBUSIERS = "rost_hum_arquebusiers"
    ROSTER_LONGBOWMEN = "rost_hum_longbowmen"
    ROSTER_FIELD_HOSPITAL = "rost_hum_field_hospital"
    ROSTER_LIGHT_CAVALRY = "rost_hum_light_cavalry"
    ROSTER_GREATSWORD_VETERANS = "rost_hum_greatsword_veterans"
    ROSTER_WITCH_HUNTERS = "rost_hum_witch_hunters"
    ROSTER_ORDER_KNIGHTS = "rost_hum_order_knights"
    ROSTER_MAGISTERS = "rost_hum_magisters"
    ROSTER_AVATAR = "rost_hum_avatar"


class HumanBuildingId(str, Enum):
    """Идентификаторы зданий людей."""

    WHEAT_FIELDS = "bld_hum_wheat_fields"
    QUARRY = "bld_hum_quarry"
    TRADING_GUILD = "bld_hum_trading_guild"
    CITY_BARRACKS = "bld_hum_city_barracks"
    WEAPONS_MANUFACTORY = "bld_hum_weapons_manufactory"
    ROYAL_STABLES = "bld_hum_royal_stables"
    MEDICAL_TENT = "bld_hum_medical_tent"
    CHAPEL_OF_LIGHT = "bld_hum_chapel_of_light"
    INQUISITION_HALL = "bld_hum_inquisition_hall"
    WATCHTOWER = "bld_hum_watchtower"
