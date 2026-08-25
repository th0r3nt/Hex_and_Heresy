"""
Перечисления идентификаторов (ID) для архетипов и рецептов найма нейтральных сил.
"""

from enum import Enum


class NeutralsUnitId(str, Enum):
    """Идентификаторы базовых архетипов нейтральных юнитов."""

    REBELS_MOB_00 = "unit_neu_rebels_mob_00"
    MARAUDERS_01 = "unit_neu_marauders_01"
    WILD_BEASTS_01 = "unit_neu_wild_beasts_01"
    DESERTER_GANG_02 = "unit_neu_deserter_gang_02"


class NeutralsWeaponId(str, Enum):
    """Идентификаторы врожденного оружия нейтральных существ."""

    BEAST_FANGS_01 = "wpn_neu_beast_fangs_01"


class NeutralsArmorId(str, Enum):
    """Идентификаторы естественной защиты нейтральных существ."""

    BEAST_HIDE_01 = "arm_neu_beast_hide_01"


class NeutralsRosterId(str, Enum):
    """Идентификаторы готовых рецептов спавна нейтральных отрядов."""

    ROSTER_REBELS = "rost_neu_rebels"
    ROSTER_MARAUDERS = "rost_neu_marauders"
    ROSTER_BEASTS = "rost_neu_beasts"
    ROSTER_DESERTERS = "rost_neu_deserters"