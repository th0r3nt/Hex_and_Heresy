"""
Реестр базовых архетипов юнитов фракции зеленокожих.
"""

from typing import Any

from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.army.models.card.unit import BaseUnitStats
from src.back.l01_domain.common import FactionRace
from src.back.gamedata.greenskins.common import GreenskinsUnitId

_RACE = FactionRace.GREENSKINS
_FACTION = "greenskins"

UNITS_LIST: dict[str, dict[str, Any]] = {
    GreenskinsUnitId.GOBLIN_SLAVES_00.value: {
        "id": GreenskinsUnitId.GOBLIN_SLAVES_00.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Гоблины-рабы",
        "tier": 0,
        "default_unit_count": 150,
        "base_stats": BaseUnitStats(
            max_hp=8.0,
            base_speed=2.5,  # Быстрее людей, так как постоянно убегают от пинков орков
            base_morale=30.0,  # Очень трусливы
            base_initiative=12,
            size_category=UnitSizeCategory.SMALL,
        ),
        "base_upkeep_food": 0.5,  # Жрут мало (в основном объедки)
        "base_upkeep_gold": 0.0,
        "lore_description": "Копошатся в грязи, копают шахты и ноют. Разбегаются при виде врага, если рядом нет надсмотрщика.",
    },
    GreenskinsUnitId.MUSHROOM_GATHERERS_00.value: {
        "id": GreenskinsUnitId.MUSHROOM_GATHERERS_00.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Гоблины-мухоморники",
        "tier": 0,
        "default_unit_count": 100,
        "base_stats": BaseUnitStats(
            max_hp=10.0,
            base_speed=2.0,
            base_morale=45.0,  # Менее трусливы, потому что под грибами
            base_initiative=10,
            size_category=UnitSizeCategory.SMALL,
        ),
        "base_upkeep_food": 0.5,
        "base_upkeep_gold": 0.0,
        "lore_description": "Работники из грибных пещер. Немного поехавшие из-за спор, часто кусают тех, кто подходит слишком близко.",
    },
    GreenskinsUnitId.YOUNG_ORCS_01.value: {
        "id": GreenskinsUnitId.YOUNG_ORCS_01.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Молодые орки",
        "tier": 1,
        "default_unit_count": 100,
        "base_stats": BaseUnitStats(
            max_hp=22.0,  # Орочья физиология крепче людской
            base_armor=0.5,
            base_speed=2.0,
            base_morale=55.0,
            base_initiative=9,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.5,
        "base_upkeep_gold": 0.2,
        "lore_description": "Основная пехота Зеленой волны (Рубилы). Берут не умением, а яростью и числом.",
    },
    GreenskinsUnitId.ORC_TRICKSTERS_01.value: {
        "id": GreenskinsUnitId.ORC_TRICKSTERS_01.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Орки-ловкачи",
        "tier": 1,
        "default_unit_count": 80,
        "base_stats": BaseUnitStats(
            max_hp=20.0,
            base_speed=2.5,
            base_morale=50.0,
            base_initiative=13,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.5,
        "base_upkeep_gold": 0.3,
        "lore_description": "Более хитрые орки, предпочитающие заходить с флангов и метать дротики, пока большие парни получают по лицу.",
    },
    GreenskinsUnitId.HARDENED_ORCS_02.value: {
        "id": GreenskinsUnitId.HARDENED_ORCS_02.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Закаленные орки",
        "tier": 2,
        "default_unit_count": 80,
        "base_stats": BaseUnitStats(
            max_hp=30.0,
            base_armor=1.0,  # Шрамы и огрубевшая кожа
            base_speed=2.0,
            base_morale=70.0,
            base_initiative=10,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 2.0,
        "base_upkeep_gold": 0.5,
        "lore_description": "Выжившие в десятках драк. Стали больше, злее и обзавелись броней из краденого металлолома. Кромсают всех подряд.",
    },
    GreenskinsUnitId.SHAMAN_APPRENTICES_02.value: {
        "id": GreenskinsUnitId.SHAMAN_APPRENTICES_02.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Ученики шамана",
        "tier": 2,
        "default_unit_count": 10,
        "base_stats": BaseUnitStats(
            max_hp=25.0,
            base_speed=2.0,
            base_morale=80.0,
            base_initiative=14,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.5,
        "base_upkeep_gold": 1.0,
        "lore_description": "Орки, чьи мозги не расплавились от первого контакта с Резонитом. Воплощение неконтролируемого магического хаоса.",
    },
    GreenskinsUnitId.IRONJAWS_03.value: {
        "id": GreenskinsUnitId.IRONJAWS_03.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Железнокожие",
        "tier": 3,
        "default_unit_count": 50,
        "base_stats": BaseUnitStats(
            max_hp=45.0,
            base_armor=2.0,
            base_speed=1.5,
            base_morale=85.0,
            base_initiative=8,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 2.5,
        "base_upkeep_gold": 1.5,
        "lore_description": "Огромные орки-ассимиляторы. Грибница в их телах буквально впаяла куски железа в их кожу и кости.",
    },
    GreenskinsUnitId.SNEAKY_GITS_03.value: {
        "id": GreenskinsUnitId.SNEAKY_GITS_03.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Банда гоблинов-проныр",
        "tier": 3,
        "default_unit_count": 40,
        "base_stats": BaseUnitStats(
            max_hp=12.0,
            base_speed=3.0,
            base_morale=50.0,
            base_initiative=16,
            size_category=UnitSizeCategory.SMALL,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 2.0,
        "lore_description": "Элита воровского ремесла. Именно они воруют у людей мушкеты, бомбы и чертежи прямо из-под носа Инквизиции.",
    },
    GreenskinsUnitId.CAVE_OGRE_04.value: {
        "id": GreenskinsUnitId.CAVE_OGRE_04.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Пещерный огр",
        "tier": 4,
        "default_unit_count": 1,
        "base_stats": BaseUnitStats(
            max_hp=400.0,
            base_armor=3.0,
            base_speed=2.5,
            base_morale=85.0,
            base_stamina=100.0,
            base_initiative=6,
            size_category=UnitSizeCategory.HUGE,
        ),
        "base_upkeep_food": 120.0,  # Жрет как чёрт
        "base_upkeep_gold": 30.0,
        "lore_description": "Чудовище из самых глубоких нор Ничьей земли. Обладает врожденной регенерацией. Интеллект как у картофелины, зато ломает стены голыми руками.",
    },
}
