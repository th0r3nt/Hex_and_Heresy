"""
Реестр базовых архетипов нейтральных юнитов.
"""

from typing import Any

from src.back.gamedata.neutrals.common import NeutralsUnitId
from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.army.models.card.unit import BaseUnitStats
from src.back.l01_domain.common import FactionRace

_RACE = FactionRace.NEUTRALS
_FACTION = "neutrals"

UNITS_LIST: dict[str, dict[str, Any]] = {
    NeutralsUnitId.REBELS_MOB_00.value: {
        "id": NeutralsUnitId.REBELS_MOB_00.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Толпа бунтовщиков",
        "tier": 0,
        "default_unit_count": 120,
        "base_stats": BaseUnitStats(
            max_hp=10.0,
            base_speed=2.0,
            base_morale=35.0,  # Низкая стойкость, легко обращаются в бегство
            base_initiative=8,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 0.5,
        "base_upkeep_gold": 0.0,
        "lore_description": "Отчаявшиеся крестьяне и беглые рабы, поднявшие восстание от голода и непосильных налогов.",
    },
    NeutralsUnitId.MARAUDERS_01.value: {
        "id": NeutralsUnitId.MARAUDERS_01.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Бродячие мародеры",
        "tier": 1,
        "default_unit_count": 80,
        "base_stats": BaseUnitStats(
            max_hp=16.0,
            base_speed=2.5,
            base_morale=50.0,
            base_initiative=11,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 0.5,
        "lore_description": "Разбойники Ничьей земли, промышляющие грабежом торговых караванов и мародерством на полях брани.",
    },
    NeutralsUnitId.WILD_BEASTS_01.value: {
        "id": NeutralsUnitId.WILD_BEASTS_01.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Одичавшие звери",
        "tier": 1,
        "default_unit_count": 40,
        "base_stats": BaseUnitStats(
            max_hp=25.0,
            base_speed=3.5,  # Высокая подвижность
            base_morale=60.0,
            base_initiative=14,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 2.0,
        "base_upkeep_gold": 0.0,
        "lore_description": "Стая мутировавших волков и пустошных тварей, рыщущих в поисках свежей плоти.",
    },
    NeutralsUnitId.DESERTER_GANG_02.value: {
        "id": NeutralsUnitId.DESERTER_GANG_02.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Шайка дезертиров",
        "tier": 2,
        "default_unit_count": 50,
        "base_stats": BaseUnitStats(
            max_hp=24.0,
            base_armor=1.0,
            base_speed=2.0,
            base_morale=65.0,
            base_initiative=11,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.5,
        "base_upkeep_gold": 1.0,
        "lore_description": "Бывшие регулярные солдаты, сбежавшие из армий со своим оружием и объединившиеся в опасные банды.",
    },
}