"""
Реестр базовых архетипов юнитов фракции эльфов.
Количество юнитов в отрядах эльфов всегда меньше, чем у других рас, но их базовые статы (инициатива, скорость) значительно выше.
"""

from typing import Any

from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.army.models.card.unit import BaseUnitStats
from src.back.l01_domain.common import FactionRace
from src.back.gamedata.elfs.common import ElfsUnitId

_RACE = FactionRace.ELFS
_FACTION = "elfs"

UNITS_LIST: dict[str, dict[str, Any]] = {
    ElfsUnitId.TEMPLE_DISCIPLES_00.value: {
        "id": ElfsUnitId.TEMPLE_DISCIPLES_00.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Ученики храма",
        "tier": 0,
        "default_unit_count": 80,
        "base_stats": BaseUnitStats(
            max_hp=15.0,
            base_speed=2.5,
            base_morale=70.0,  # Гораздо дисциплинированнее обычных рабочих
            base_initiative=12,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 0.5,  # Эльфы едят мало
        "base_upkeep_gold": 0.5,
        "lore_description": "Младшие эльфы, которым еще нет и пятисот лет. Выполняют грязную работу, извлекая резонит из пролитой крови на полях брани.",
    },
    ElfsUnitId.WASTELAND_SEEKERS_00.value: {
        "id": ElfsUnitId.WASTELAND_SEEKERS_00.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Ищущие в пустошах",
        "tier": 0,
        "default_unit_count": 60,
        "base_stats": BaseUnitStats(
            max_hp=12.0,
            base_speed=4.0,  # Очень быстрые разведчики
            base_morale=65.0,
            base_initiative=16,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 0.5,
        "base_upkeep_gold": 1.0,
        "lore_description": "Наблюдатели. Не вступают в бой, но накладывают 'Метку пустоты' на врагов, увеличивая урон от эльфийских стрелков.",
    },
    ElfsUnitId.ITHILIEN_GUARDS_01.value: {
        "id": ElfsUnitId.ITHILIEN_GUARDS_01.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Итильенские стражи",
        "tier": 1,
        "default_unit_count": 60,
        "base_stats": BaseUnitStats(
            max_hp=25.0,
            base_speed=2.5,
            base_morale=85.0,
            base_initiative=14,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 2.0,
        "lore_description": "Сражаются в пугающей, абсолютной тишине. Невосприимчивы к животному страху, паникуют лишь от сбоев магии.",
    },
    ElfsUnitId.ITHILIEN_ARCHERS_01.value: {
        "id": ElfsUnitId.ITHILIEN_ARCHERS_01.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Итильенские лучники",
        "tier": 1,
        "default_unit_count": 60,
        "base_stats": BaseUnitStats(
            max_hp=15.0,
            base_speed=2.5,
            base_morale=75.0,
            base_initiative=18,  # Стеклянные пушки, бьют первыми
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 2.0,
        "lore_description": "Рассчитывают траекторию еще до того, как враг сделает первый шаг. Выкашивают пехоту до начала ближнего боя.",
    },
    ElfsUnitId.BLADE_DANCERS_02.value: {
        "id": ElfsUnitId.BLADE_DANCERS_02.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Танцующие-с-клинками",
        "tier": 2,
        "default_unit_count": 40,
        "base_stats": BaseUnitStats(
            max_hp=22.0,
            base_speed=3.5,  # Исключительно мобильная пехота
            base_morale=90.0,
            base_initiative=17,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 4.0,
        "lore_description": "Профессиональные убийцы. Двигаются с такой скоростью, что их силуэты размываются. Бессильны в глухой позиционной обороне.",
    },
    ElfsUnitId.RESONITE_PRIESTS_02.value: {
        "id": ElfsUnitId.RESONITE_PRIESTS_02.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Жрецы резонита",
        "tier": 2,
        "default_unit_count": 15,
        "base_stats": BaseUnitStats(
            max_hp=40.0,
            base_speed=2.0,
            base_morale=95.0,
            base_initiative=12,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 6.0,
        "lore_description": "Маги среднего звена. Стреляют плазмой и используют резонитовые барьеры, поглощающие первые атаки каждого такта.",
    },
    ElfsUnitId.KRON_KERN_MASTERS_03.value: {
        "id": ElfsUnitId.KRON_KERN_MASTERS_03.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Мастера лука Крон-Керна",
        "tier": 3,
        "default_unit_count": 30,
        "base_stats": BaseUnitStats(
            max_hp=30.0,
            base_speed=2.5,
            base_morale=95.0,
            base_initiative=15,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 8.0,
        "lore_description": "Снайперы с тысячелетним опытом. Их алгоритмы наведения игнорируют пушечное мясо и целятся точно во вражеских командиров.",
    },
    ElfsUnitId.ILLUSIONIST_MAGES_03.value: {
        "id": ElfsUnitId.ILLUSIONIST_MAGES_03.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Маги-иллюзионисты",
        "tier": 3,
        "default_unit_count": 15,
        "base_stats": BaseUnitStats(
            max_hp=35.0,
            base_speed=2.0,
            base_morale=90.0,
            base_initiative=16,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 8.0,
        "lore_description": "Саппорты поля боя. Искажают свет, создавая голограммы союзников. Враг тратит выносливость, нанося удары по пустоте.",
    },
    ElfsUnitId.CRYSTAL_SENTINELS_03.value: {
        "id": ElfsUnitId.CRYSTAL_SENTINELS_03.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Кристальные часовые",
        "tier": 3,
        "default_unit_count": 20,
        "base_stats": BaseUnitStats(
            max_hp=80.0,
            base_armor=5.0,  # Врожденная броня из кристаллизованной плоти
            base_speed=1.5,  # Единственные медленные эльфы
            base_morale=100.0,  # Боли они уже не чувствуют
            base_initiative=8,
            size_category=UnitSizeCategory.MEDIUM,
        ),
        "base_upkeep_food": 0.0,  # Они больше не питаются органикой
        "base_upkeep_gold": 10.0,
        "lore_description": "Эльфы на терминальной стадии Изъяна Монолита. Почти полностью состоят из камня и резонита. Медленные, тяжелые, несокрушимые.",
    },
    ElfsUnitId.GHOST_ARK_04.value: {
        "id": ElfsUnitId.GHOST_ARK_04.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Призрачный ковчег",
        "tier": 4,
        "default_unit_count": 5,  # 1 ковчег и экипаж
        "base_stats": BaseUnitStats(
            max_hp=350.0,
            base_armor=3.0,
            base_speed=2.0,
            base_morale=100.0,
            base_initiative=10,
            size_category=UnitSizeCategory.LARGE,
        ),
        "base_upkeep_food": 1.0,
        "base_upkeep_gold": 25.0,
        "lore_description": "Левитирующий гигантский кристалл. Создает вокруг себя ауру нулевой гравитации, из-за чего союзники перестают тратить выносливость на марш.",
    },
    ElfsUnitId.EMERALD_DRAGON_LORDS_05.value: {
        "id": ElfsUnitId.EMERALD_DRAGON_LORDS_05.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Изумрудные драконы",
        "tier": 5,
        "default_unit_count": 3,
        "base_stats": BaseUnitStats(
            max_hp=200.0,
            base_armor=5.0,
            base_speed=4.0,
            base_morale=100.0,
            base_initiative=16,
            size_category=UnitSizeCategory.HUGE,
        ),
        "base_upkeep_food": 10.0,
        "base_upkeep_gold": 40.0,
        "lore_description": "Жуткие мутанты Ничьей земли, подчиненные телепатией эльфов. Извергают кислоту, расщепляющую имперскую сталь до атомов.",
    },
    ElfsUnitId.CELESTIAL_COMMANDER_06.value: {
        "id": ElfsUnitId.CELESTIAL_COMMANDER_06.value,
        "race": _RACE,
        "faction_id": _FACTION,
        "name": "Небесный полководец",
        "tier": 6,
        "default_unit_count": 1,
        "base_stats": BaseUnitStats(
            max_hp=800.0,
            base_armor=10.0,
            base_speed=3.0,
            base_morale=100.0,
            base_initiative=20,
            size_category=UnitSizeCategory.HUGE,
        ),
        "base_upkeep_food": 0.0,
        "base_upkeep_gold": 150.0,
        "lore_description": "Древнейший эльф. Божество на поле боя, левитирующее в позе лотоса. Его плоть - иллюзия, а смерть - это сверхновая звезда.",
    },
}
