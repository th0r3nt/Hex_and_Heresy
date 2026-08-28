"""
Перечисления идентификаторов (ID) для снаряжения, архетипов и рецептов фракции наемников.
"""

from enum import Enum


class MercenaryWeaponId(str, Enum):
    """Идентификаторы оружия наемников."""

    BEAR_CLAWS_01 = "wpn_mer_bear_claws_01"
    HEROIC_ARSENAL_02 = "wpn_mer_heroic_arsenal_02"
    COMPANY_CROSSBOW_01 = "wpn_mer_company_crossbow_01"
    AERIAL_BOMBS_03 = "wpn_mer_aerial_bombs_03"


class MercenaryArmorId(str, Enum):
    """Идентификаторы брони наемников."""

    COMPANY_BRIGANDINE_01 = "arm_mer_company_brigandine_01"
    BEAR_BARDING_01 = "arm_mer_bear_barding_01"
    ADVENTURER_GEAR_02 = "arm_mer_adventurer_gear_02"
    ZEPPELIN_HULL_03 = "arm_mer_zeppelin_hull_03"


class MercenaryAccessoryId(str, Enum):
    """Идентификаторы аксессуаров наемников."""

    ADVANCE_PAYMENT_01 = "acc_mer_advance_payment_01"
    TAMER_WHIP_01 = "acc_mer_tamer_whip_01"
    QUEST_ARTIFACT_02 = "acc_mer_quest_artifact_02"
    BOMBSIGHT_03 = "acc_mer_bombsight_03"


class MercenaryUnitId(str, Enum):
    """Идентификаторы базовых архетипов юнитов наемников."""

    FREE_COMPANY_01 = "unit_mer_free_company_01"
    BEAR_TAMERS_01 = "unit_mer_bear_tamers_01"
    HEROES_FOR_HIRE_02 = "unit_mer_heroes_for_hire_02"
    CORSAIRS_03 = "unit_mer_corsairs_03"


class MercenaryRosterId(str, Enum):
    """Идентификаторы готовых контрактов (рецептов найма) наемников."""

    CONTRACT_FREE_COMPANY = "rost_mer_contract_free_company"
    CONTRACT_BEAR_TAMERS = "rost_mer_contract_bear_tamers"
    CONTRACT_HEROES = "rost_mer_contract_heroes"
    CONTRACT_CORSAIRS = "rost_mer_contract_corsairs"


class MercenaryHeroId(str, Enum):
    """
    Идентификаторы легендарных вольных капитанов.

    Лордов и полководцев у наемников нет: это нейтральная сила без
    цитадели и правителя, за нее не играют.
    """

    CAPTAIN_VANCE = "hero_mer_captain_vance"
    LADY_BEATRICE = "hero_mer_lady_beatrice"
    HECTOR = "hero_mer_hector"
