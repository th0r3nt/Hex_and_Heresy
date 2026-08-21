"""
Реестр базовых архетипов юнитов фракции наемников.
"""

from typing import Any

from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.army.models.card.unit import BaseUnitStats
from src.back.l01_domain.common import FactionRace
from src.back.gamedata.mercenaries.common import MercenaryUnitId

_RACE = FactionRace.MERCENARIES
_FACTION = "mercenaries"

UNITS_LIST: dict[str, dict[str, Any]] = {
    MercenaryUnitId.FREE_COMPANY_01.value: {
        "id": MercenaryUnitId.FREE_COMPANY_01.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Свободная рота арбалетчиков",
        "tier": 1,
        "default_unit_count": 70,
        "base_stats": BaseUnitStats(
            max_hp=15.0,
            base_speed=2.0,
            base_morale=65.0,  # Хорошая дисциплина, пока не пахнет смертью
            base_initiative=12,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 3.0,  # Дорогие в содержании
        "lore_description": "Дезертиры, которые ушли из имперской армии ради золота баронств или других лордов.",
    },
    MercenaryUnitId.BEAR_TAMERS_01.value: {
        "id": MercenaryUnitId.BEAR_TAMERS_01.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Укротители боевых медведей",
        "tier": 1,
        "default_unit_count": 60,  # 20 людей + 40 медведей
        "base_stats": BaseUnitStats(
            max_hp=40.0,  # Медведи очень живучие
            base_speed=3.0,
            base_morale=55.0,
            base_initiative=10,
            size_category=UnitSizeCategory.LARGE,
        ),
        "base_upkeep_food": 5.0,  # Жрут ОЧЕНЬ много еды
        "base_upkeep_gold": 2.0,
        "lore_description": "Отличные танки для ранней игры. Но если еда кончится, медведи сожрут своих же нанимателей.",
    },
    MercenaryUnitId.HEROES_FOR_HIRE_02.value: {
        "id": MercenaryUnitId.HEROES_FOR_HIRE_02.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Герои по найму",
        "tier": 2,
        "default_unit_count": 4,  # Рыцарь, эльфийка, гном, жрец
        "base_stats": BaseUnitStats(
            max_hp=120.0,
            base_armor=5.0,
            base_speed=3.0,
            base_morale=95.0,
            base_initiative=15,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 10.0,
        "lore_description": "Отряд с идеальной синергией. Очень сильны, но требуют не только золота, но и артефактов на свой найм.",
    },
    MercenaryUnitId.CORSAIRS_03.value: {
        "id": MercenaryUnitId.CORSAIRS_03.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Корсары",
        "tier": 3,
        "default_unit_count": 1,  # 1 дирижабль (с экипажем внутри)
        "base_stats": BaseUnitStats(
            max_hp=300.0,
            base_armor=4.0,
            base_speed=3.0,
            base_morale=80.0,
            base_initiative=10,
            size_category=UnitSizeCategory.HUGE,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 15.0,
        "lore_description": "Пиратский цеппелин капитана Вэнса. Зависает над землей, сбрасывая бомбы. Неуязвим для пехоты.",
    },
}
