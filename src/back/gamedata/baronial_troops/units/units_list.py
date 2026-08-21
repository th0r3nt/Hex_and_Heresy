"""
Реестр базовых архетипов юнитов фракции баронских войск.
"""

from typing import Any

from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.army.models.card.unit import BaseUnitStats
from src.back.l01_domain.common import FactionRace
from src.back.gamedata.baronial_troops.common import BaronialUnitId

_RACE = FactionRace.BARONIAL_TROOPS
_FACTION = "baronial_troops"

UNITS_LIST: dict[str, dict[str, Any]] = {
    BaronialUnitId.SERFS_MOB_00.value: {
        "id": BaronialUnitId.SERFS_MOB_00.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Толпа крепостных",
        "tier": 0,
        "default_unit_count": 150,
        "base_stats": BaseUnitStats(
            max_hp=10.0,
            base_speed=2.0,
            base_morale=35.0,  # Очень легко впадают в панику
            base_initiative=8,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 0.5,  # Барон их почти не кормит
        "base_upkeep_gold": 0.0,
        "lore_description": "Расходный материал. Барон платит за них только гнилой едой. Вне своего родного замка разбегаются при первых же потерях.",
    },
    BaronialUnitId.TAX_COLLECTORS_00.value: {
        "id": BaronialUnitId.TAX_COLLECTORS_00.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Сборщики податей",
        "tier": 0,
        "default_unit_count": 20,
        "base_stats": BaseUnitStats(
            max_hp=12.0,
            base_speed=3.0,  # Быстро убегают
            base_morale=45.0,
            base_initiative=10,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 1.0,
        "lore_description": "Не умеют драться. Выезжают в Ничью землю и пассивно генерируют золото (грабят деревни), но являются легкой добычей.",
    },
    BaronialUnitId.SIGNALMEN_00.value: {
        "id": BaronialUnitId.SIGNALMEN_00.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Сигнальщики на вышках",
        "tier": 0,
        "default_unit_count": 20,
        "base_stats": BaseUnitStats(
            max_hp=10.0,
            base_speed=2.0,
            base_morale=50.0,
            base_initiative=12,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 0.5,
        "lore_description": "Самая дешевая разведка. Снимают туман войны с соседних зон и подают сигналы основной армии.",
    },
    BaronialUnitId.CASTLE_GUARDS_01.value: {
        "id": BaronialUnitId.CASTLE_GUARDS_01.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Баронская гвардия",
        "tier": 1,
        "default_unit_count": 100,
        "base_stats": BaseUnitStats(
            max_hp=20.0,
            base_speed=2.0,
            base_morale=65.0,
            base_initiative=10,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 1.0,
        "lore_description": "Основа баронской армии. Стоят насмерть, пока им платят. Если не перемещались в этот такт (стоят в обороне), получают огромный бонус к выживаемости.",
    },
    BaronialUnitId.OUTPOST_SHOOTERS_01.value: {
        "id": BaronialUnitId.OUTPOST_SHOOTERS_01.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Стрелки заставы",
        "tier": 1,
        "default_unit_count": 80,
        "base_stats": BaseUnitStats(
            max_hp=15.0,
            base_speed=2.0,
            base_morale=55.0,
            base_initiative=9,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 1.0,
        "lore_description": "Наемные арбалетчики, привыкшие стрелять из-за глухих укрытий по безоружным торговцам. В чистом поле чувствуют себя неуютно.",
    },
    BaronialUnitId.VETERAN_MERCENARIES_02.value: {
        "id": BaronialUnitId.VETERAN_MERCENARIES_02.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Наемники-ветераны",
        "tier": 2,
        "default_unit_count": 80,
        "base_stats": BaseUnitStats(
            max_hp=25.0,
            base_armor=1.0,
            base_speed=2.0,
            base_morale=75.0,
            base_initiative=11,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.5,
        "base_upkeep_gold": 2.0,  # Дорогие в содержании
        "lore_description": "Угрюмые мужики, которым плевать, кого убивать: орков или имперских инквизиторов. Отлично вскрывают 'консервные банки' врага.",
    },
    BaronialUnitId.SUPPLY_WAGON_02.value: {
        "id": BaronialUnitId.SUPPLY_WAGON_02.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Обоз с провизией",
        "tier": 2,
        "default_unit_count": 30,  # Охрана и повозка
        "base_stats": BaseUnitStats(
            max_hp=30.0,
            base_speed=1.5,
            base_morale=60.0,
            base_initiative=6,
            size_category=UnitSizeCategory.LARGE,
        ),
        "base_upkeep_food": -50.0,  # Генерирует еду для армии
        "base_upkeep_gold": 13.0,
        "lore_description": "Баронская логистика. Избавляет армию от дезертирства и штрафов при нахождении в глубоких пустошах.",
    },
    BaronialUnitId.EXECUTIONERS_03.value: {
        "id": BaronialUnitId.EXECUTIONERS_03.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Палачи баронства",
        "tier": 3,
        "default_unit_count": 30,
        "base_stats": BaseUnitStats(
            max_hp=40.0,
            base_speed=2.0,
            base_morale=90.0,
            base_initiative=12,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 3.0,
        "lore_description": "Мрачные громилы в глухих масках. Выходят на поле боя только ради того, чтобы наводить ужас на крестьян и рубить головы тем, кто дрогнул.",
    },
    BaronialUnitId.TAME_OGRE_04.value: {
        "id": BaronialUnitId.TAME_OGRE_04.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Ручной огр",
        "tier": 4,
        "default_unit_count": 1,
        "base_stats": BaseUnitStats(
            max_hp=450.0,
            base_armor=3.0,
            base_speed=2.5,
            base_morale=70.0,
            base_stamina=100.0,
            base_initiative=8,
            size_category=UnitSizeCategory.HUGE,
        ),
        "base_upkeep_food": 10.0,
        "base_upkeep_gold": 2.0,
        "lore_description": "Бароны ловят их в пустошах и сажают на цепь. Огр зашивается в стальные листы, получая иммунитет к легким стрелам.",
    },
    BaronialUnitId.DESERTER_KNIGHTS_05.value: {
        "id": BaronialUnitId.DESERTER_KNIGHTS_05.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Рыцари-дезертиры",
        "tier": 5,
        "default_unit_count": 30,
        "base_stats": BaseUnitStats(
            max_hp=60.0,
            base_armor=2.0,
            base_speed=3.5,
            base_morale=80.0,
            base_initiative=13,
            size_category=UnitSizeCategory.LARGE,
        ),
        "base_upkeep_food": 3.0,
        "base_upkeep_gold": 8.0,  # Требуют тройного жалования золотом
        "lore_description": "Бывшие имперские офицеры, променявшие веру на полновесные серебряники. Их натиск смертоносен.",
    },
    BaronialUnitId.BARON_CARRIAGE_06.value: {
        "id": BaronialUnitId.BARON_CARRIAGE_06.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Карета Барона",
        "tier": 6,
        "default_unit_count": 1,
        "base_stats": BaseUnitStats(
            max_hp=500.0,
            base_armor=5.0,
            base_speed=2.0,
            base_morale=100.0,  # Барон уверен в себе
            base_initiative=10,
            size_category=UnitSizeCategory.HUGE,
        ),
        "base_upkeep_food": 5.0,
        "base_upkeep_gold": 15.0,
        "lore_description": "Бронированная крепость на колесах, из которой правитель руководит боем. Ощетинилась арбалетами и пушками.",
    },
}
