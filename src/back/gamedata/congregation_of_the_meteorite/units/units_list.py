"""
Реестр базовых архетипов юнитов фракции 'Паства метеорита'.
Отряды варьируются от бесплатного пушечного мяса (зомби) до ультимативных демонов и драконов.
"""

from typing import Any

from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.army.models.card.unit import BaseUnitStats
from src.back.l01_domain.common import FactionRace
from src.back.gamedata.congregation_of_the_meteorite.common import CotmUnitId

_RACE = FactionRace.CONGREGATION_OF_THE_METEORITE
_FACTION = "congregation_of_the_meteorite"

UNITS_LIST: dict[str, dict[str, Any]] = {
    CotmUnitId.GOBLIN_LOOTERS_00.value: {
        "id": CotmUnitId.GOBLIN_LOOTERS_00.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Гоблины-мародеры",
        "tier": 0,
        "default_unit_count": 110,
        "base_stats": BaseUnitStats(
            max_hp=10.0,
            base_speed=2.5,
            base_morale=35.0,
            base_initiative=12,
            size_category=UnitSizeCategory.SMALL,
        ),
        "base_upkeep_food": 0.5,
        "base_upkeep_gold": 0.5,
        "lore_description": "Жадные, быстрые, слабые. Копошатся на полях сражений, принося золото, но часто крадут часть добычи себе.",
    },
    CotmUnitId.NECROMANCERS_00.value: {
        "id": CotmUnitId.NECROMANCERS_00.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Некроманты",
        "tier": 0,
        "default_unit_count": 200,  # 20 магов + 180 скелетов
        "base_stats": BaseUnitStats(
            max_hp=15.0,  # Усредненное ХП скелета/некроманта
            base_speed=1.5,
            base_morale=80.0,  # Скелеты не ведают страха
            base_initiative=8,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 0.5,  # Мертвецы не едят, едят только маги
        "base_upkeep_gold": 1.0,
        "lore_description": "Группа жрецов, окруженная поднятыми скелетами. Скелеты принимают урон, но если убить жрецов - кости рассыпаются.",
    },
    CotmUnitId.ZOMBIE_HORDE_01.value: {
        "id": CotmUnitId.ZOMBIE_HORDE_01.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Орда зомби",
        "tier": 1,
        "default_unit_count": 230,
        "base_stats": BaseUnitStats(
            max_hp=30.0,  # Чудовищно живучие для своего тира
            base_armor=0.0,
            base_speed=1.0,  # Чудовищно медленные
            base_morale=100.0,  # Иммунны к страху
            base_initiative=2,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,  # Жрут плоть
        "base_upkeep_gold": 0.0,
        "lore_description": "Мертвая плоть, гальванизированная резонитом. Идут медленно, но не останавливаются ни перед чем.",
    },
    CotmUnitId.LESSER_DEMONS_01.value: {
        "id": CotmUnitId.LESSER_DEMONS_01.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Низшие демоны",
        "tier": 1,
        "default_unit_count": 120,
        "base_stats": BaseUnitStats(
            max_hp=20.0,
            base_speed=2.5,
            base_morale=60.0,
            base_initiative=12,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 0.0,
        "base_upkeep_gold": 2.0,
        "lore_description": "Плазменные мутанты из разломов. При смерти их нестабильная оболочка взрывается, нанося урон всем вокруг.",
    },
    CotmUnitId.ORC_GLADIATORS_02.value: {
        "id": CotmUnitId.ORC_GLADIATORS_02.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Орки-гладиаторы",
        "tier": 2,
        "default_unit_count": 70,
        "base_stats": BaseUnitStats(
            max_hp=35.0,
            base_armor=1.0,
            base_speed=2.0,
            base_morale=85.0,
            base_initiative=11,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 2.0,
        "base_upkeep_gold": 1.0,
        "lore_description": "Абсолютно безумные бойцы. Чем больше боли они получают, тем сильнее бьют в ответ.",
    },
    CotmUnitId.DARK_MEN_AT_ARMS_02.value: {
        "id": CotmUnitId.DARK_MEN_AT_ARMS_02.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Темные латники",
        "tier": 2,
        "default_unit_count": 50,
        "base_stats": BaseUnitStats(
            max_hp=25.0,
            base_armor=2.0,
            base_speed=2.0,
            base_morale=70.0,
            base_initiative=10,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.5,
        "base_upkeep_gold": 2.0,
        "lore_description": "Бывшие имперские солдаты, продавшие души Пастве. Восстанавливают силы, проливая чужую кровь.",
    },
    CotmUnitId.GHOSTS_02.value: {
        "id": CotmUnitId.GHOSTS_02.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Призраки",
        "tier": 2,
        "default_unit_count": 40,
        "base_stats": BaseUnitStats(
            max_hp=15.0,
            base_speed=3.0,  # Летают, игнорируют грязь
            base_morale=100.0,
            base_initiative=14,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 0.0,
        "base_upkeep_gold": 3.0,
        "lore_description": "Электромагнитные слепки душ. Физические атаки проходят сквозь них с шансом 50%, но они крайне уязвимы к магии.",
    },
    CotmUnitId.WEREWOLVES_03.value: {
        "id": CotmUnitId.WEREWOLVES_03.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Оборотни",
        "tier": 3,
        "default_unit_count": 30,
        "base_stats": BaseUnitStats(
            max_hp=50.0,
            base_armor=1.0,
            base_speed=4.0,  # В форме волка
            base_morale=80.0,
            base_initiative=16,
            size_category=UnitSizeCategory.LARGE,
        ),
        "base_upkeep_food": 4.0,  # Жрут очень много мяса
        "base_upkeep_gold": 1.0,
        "lore_description": "На базе они - слабые люди. В Ничьей земле - гигантские волки с дикой скоростью и регенерацией.",
    },
    CotmUnitId.ELF_BLOODLETTERS_03.value: {
        "id": CotmUnitId.ELF_BLOODLETTERS_03.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Эльфийские кровопускатели",
        "tier": 3,
        "default_unit_count": 30,
        "base_stats": BaseUnitStats(
            max_hp=25.0,
            base_speed=3.5,
            base_morale=85.0,
            base_initiative=17,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 5.0,
        "lore_description": "Предатели своего народа. Стеклянные пушки. Нулевая броня, но их атаки накладывают жуткое кровотечение.",
    },
    CotmUnitId.BLOODLETTING_MAGE_03.value: {
        "id": CotmUnitId.BLOODLETTING_MAGE_03.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Маг кровопускания",
        "tier": 3,
        "default_unit_count": 10,
        "base_stats": BaseUnitStats(
            max_hp=30.0,
            base_speed=2.0,
            base_morale=90.0,
            base_initiative=10,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 4.0,
        "lore_description": "Саппорты. Лечат элитные отряды прямо в бою, вытягивая жизненные силы из собственных рабов.",
    },
    CotmUnitId.BOMBERS_03.value: {
        "id": CotmUnitId.BOMBERS_03.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Подрыватели",
        "tier": 3,
        "default_unit_count": 40,
        "base_stats": BaseUnitStats(
            max_hp=15.0,
            base_speed=2.5,
            base_morale=60.0,
            base_initiative=13,
            size_category=UnitSizeCategory.SMALL,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 3.0,
        "lore_description": "Гоблины-камикадзе с порохом. С равным успехом взрывают как врагов, так и союзников.",
    },
    CotmUnitId.MUMMY_SUMMONERS_04.value: {
        "id": CotmUnitId.MUMMY_SUMMONERS_04.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Призыватели мумий",
        "tier": 4,
        "default_unit_count": 100,  # 20 жрецов + 80 мумий
        "base_stats": BaseUnitStats(
            max_hp=40.0,
            base_armor=2.0,
            base_speed=1.5,
            base_morale=100.0,
            base_initiative=8,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 8.0,
        "lore_description": "Жрецы, поднимающие элитную нежить. Мумии не только впитывают урон, но и заражают атакующих трупным ядом.",
    },
    CotmUnitId.GREEDY_DRAGON_05.value: {
        "id": CotmUnitId.GREEDY_DRAGON_05.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Алчный дракон",
        "tier": 5,
        "default_unit_count": 1,
        "base_stats": BaseUnitStats(
            max_hp=600.0,
            base_armor=8.0,
            base_speed=4.0,  # Летает
            base_morale=90.0,
            base_stamina=100.0,
            base_initiative=18,
            size_category=UnitSizeCategory.HUGE,
        ),
        "base_upkeep_food": 15.0,
        "base_upkeep_gold": 80.0,  # Буквально пожирает казну
        "lore_description": "Колоссальная AoE-машина смерти. Но каждый такт его найма высасывает из казны фракции горы золота.",
    },
    CotmUnitId.IMMORTAL_RIDERS_05.value: {
        "id": CotmUnitId.IMMORTAL_RIDERS_05.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Бессмертные всадники",
        "tier": 5,
        "default_unit_count": 30,
        "base_stats": BaseUnitStats(
            max_hp=60.0,
            base_armor=3.0,
            base_speed=5.0,
            base_morale=100.0,
            base_initiative=15,
            size_category=UnitSizeCategory.LARGE,
        ),
        "base_upkeep_food": 0.0,
        "base_upkeep_gold": 15.0,
        "lore_description": "Элитная призрачная кавалерия. Если они погибают, их сущность автоматически воскрешается на базе через несколько тактов.",
    },
    CotmUnitId.DOOM_HARBINGERS_06.value: {
        "id": CotmUnitId.DOOM_HARBINGERS_06.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Предвестники рока",
        "tier": 6,
        "default_unit_count": 1,  # В итоге превращаются в 1 Властителя Ада
        "base_stats": BaseUnitStats(
            max_hp=1000.0,
            base_armor=15.0,
            base_speed=3.0,
            base_morale=100.0,
            base_stamina=100.0,
            base_initiative=20,
            size_category=UnitSizeCategory.HUGE,
        ),
        "base_upkeep_food": 0.0,
        "base_upkeep_gold": 100.0,
        "lore_description": "Карточка-ритуал. Приносят себя в жертву, чтобы призвать Властителя Ада, способного убить любой отряд одним ударом.",
    },
}
