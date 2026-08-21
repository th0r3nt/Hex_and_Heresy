"""
Реестр зданий фракции эльфов.
Эльфийская архитектура левитирует над землей, состоит из гладких резонитовых кристаллов и функционирует в абсолютной тишине.
"""

from typing import Any

from src.back.l01_domain.factions.constants import BuildingCategory, ResourceType
from src.back.l01_domain.factions.models.buildings import BuildingUpgrade
from src.back.l01_domain.maps.constants import TerritoryZoneType
from src.back.gamedata.elfs.common import ElfsBuildingId, ElfsUnitId

_FACTION = "elfs"

BUILDINGS_LIST: dict[str, dict[str, Any]] = {
    # ==================================================================
    # ЭКОНОМИКА
    # ==================================================================
    ElfsBuildingId.ESSENCE_EXTRACTORS.value: {
        "id": ElfsBuildingId.ESSENCE_EXTRACTORS.value,
        "faction_id": _FACTION,
        "name": "Экстракторы эссенции",
        "lore_description": "Изящные шпили, которые вытягивают остаточный резонит из почвы и пролитой крови. Никаких кирок, только чистая гармония.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 20.0,
        "cost_material": 50.0,
        "construction_ticks": 1,
        "requires_workers": True,
        "resource_output_per_worker": {ResourceType.MATERIAL: 80.0},
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_elf_resonant_filters",
                name="Резонансные фильтры",
                lore_description="Тонкая настройка кристаллов позволяет улавливать даже малейшие колебания фона.",
                cost_gold=50.0,
                cost_material=30.0,
            ),
        ],
    },
    ElfsBuildingId.CRYSTAL_GARDENS.value: {
        "id": ElfsBuildingId.CRYSTAL_GARDENS.value,
        "faction_id": _FACTION,
        "name": "Хрустальные сады",
        "lore_description": "Здесь нет грязной земли. Эльфы синтезируют питательный нектар прямо из света и воды.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 10.0,
        "cost_material": 60.0,
        "construction_ticks": 1,
        "requires_workers": True,
        "resource_output_per_worker": {
            ResourceType.FOOD: 150.0
        },  # Эльфам нужно меньше еды, но сады и производят меньше ферм
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_elf_dew_condensers",
                name="Конденсаторы росы",
                lore_description="Увеличивает плотность питательных веществ в каждой капле нектара.",
                cost_gold=30.0,
                cost_material=40.0,
            ),
        ],
    },
    ElfsBuildingId.SILENT_MARKET.value: {
        "id": ElfsBuildingId.SILENT_MARKET.value,
        "faction_id": _FACTION,
        "name": "Обитель белого шума",
        "lore_description": "Здесь не торгуются голосом. Любой громкий звук наказывается. Обмен идет через телепатические импульсы.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 150.0,
        "cost_material": 200.0,
        "construction_ticks": 2,
        "requires_workers": False,
        "resource_output_per_worker": {},
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_elf_telepathic_network",
                name="Телепатическая сеть",
                lore_description="Позволяет навязывать свои торговые условия представителям низших рас еще до начала переговоров.",
                cost_gold=100.0,
                cost_material=100.0,
            ),
        ],
        "special_rules": "Монополия тишины: пассивно генерирует золото, значительно увеличивает выгоду от дипломатических торговых соглашений.",
    },
    # ==================================================================
    # ВОЕННАЯ ИНФРАСТРУКТУРА
    # ==================================================================
    ElfsBuildingId.SANCTUARY_OF_BLADES.value: {
        "id": ElfsBuildingId.SANCTUARY_OF_BLADES.value,
        "faction_id": _FACTION,
        "name": "Святилище клинков",
        "lore_description": "Залы, где молодые эльфы сотни лет оттачивают смертоносный танец с резонитовыми лезвиями.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 50.0,
        "cost_material": 100.0,
        "construction_ticks": 1,
        "unlock_tier": 1,
        "unlocked_unit_ids": [
            ElfsUnitId.WASTELAND_SEEKERS_00.value,
            ElfsUnitId.ITHILIEN_GUARDS_01.value,
            ElfsUnitId.ITHILIEN_ARCHERS_01.value,
            ElfsUnitId.BLADE_DANCERS_02.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_elf_halls_of_silence",
                name="Залы безмолвия",
                lore_description="Тренировки в вакууме. Оттачивает реакцию до идеала.",
                cost_gold=80.0,
                cost_material=120.0,
            ),
        ],
    },
    ElfsBuildingId.SPIRE_OF_SEERS.value: {
        "id": ElfsBuildingId.SPIRE_OF_SEERS.value,
        "faction_id": _FACTION,
        "name": "Шпиль Провидцев",
        "lore_description": "Башня, где иллюзионисты и жрецы учатся искажать реальность силой мысли.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 100.0,
        "cost_material": 150.0,
        "construction_ticks": 2,
        "unlock_tier": 2,
        "unlocked_unit_ids": [
            ElfsUnitId.RESONITE_PRIESTS_02.value,
            ElfsUnitId.ILLUSIONIST_MAGES_03.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_elf_focal_crystals",
                name="Фокусные кристаллы",
                lore_description="Дает жрецам постоянный бонус к инициативе при найме.",
                cost_gold=120.0,
                cost_material=180.0,
            ),
        ],
    },
    ElfsBuildingId.ASTRAL_FORGE.value: {
        "id": ElfsBuildingId.ASTRAL_FORGE.value,
        "faction_id": _FACTION,
        "name": "Астральная кузня",
        "lore_description": "Здесь не стучат молотами. Экипировка выращивается из первичной взвеси под звуки камертонов.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 150.0,
        "cost_material": 250.0,
        "construction_ticks": 2,
        "unlock_tier": 3,
        "unlocked_unit_ids": [
            ElfsUnitId.KRON_KERN_MASTERS_03.value,
            ElfsUnitId.CRYSTAL_SENTINELS_03.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_elf_isotopic_anvils",
                name="Изотопные матрицы",
                lore_description="Позволяют быстрее 'печатать' тяжелую кристальную броню. Снижает стоимость найма элиты.",
                cost_gold=200.0,
                cost_material=300.0,
            ),
        ],
    },
    ElfsBuildingId.FLOATING_SHIPYARD.value: {
        "id": ElfsBuildingId.FLOATING_SHIPYARD.value,
        "faction_id": _FACTION,
        "name": "Парящая верфь",
        "lore_description": "Антигравитационные стапели, где собираются Призрачные Ковчеги и седла для драконов.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 250.0,
        "cost_material": 400.0,
        "construction_ticks": 3,
        "unlock_tier": 4,
        "unlocked_unit_ids": [
            ElfsUnitId.GHOST_ARK_04.value,
            ElfsUnitId.EMERALD_DRAGON_LORDS_05.value,
        ],
        "available_upgrades": [],
    },
    ElfsBuildingId.MONOLITH_OF_STASIS.value: {
        "id": ElfsBuildingId.MONOLITH_OF_STASIS.value,
        "faction_id": _FACTION,
        "name": "Монолит Стазиса",
        "lore_description": "Святилище, в котором погружены в сон древнейшие эльфы. Место абсолютного покоя.",
        "category": BuildingCategory.UNIQUE,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 500.0,
        "cost_material": 1000.0,
        "construction_ticks": 4,
        "unlock_tier": 6,
        "unlocked_unit_ids": [
            ElfsUnitId.CELESTIAL_COMMANDER_06.value,
        ],
        "available_upgrades": [],
        "special_rules": "Пробуждение бога: позволяет призвать на поле боя ультимативного Небесного Полководца. Наличие этого здания вызывает тревогу у всех остальных фракций в мире.",
    },
    # ==================================================================
    # КУЛЬТУРА И ОБОРОНА
    # ==================================================================
    ElfsBuildingId.CHAMBER_OF_ECHOES.value: {
        "id": ElfsBuildingId.CHAMBER_OF_ECHOES.value,
        "faction_id": _FACTION,
        "name": "Зал Эхо",
        "lore_description": "Архитектура, поглощающая звуки. Любая вражеская армия, заходящая сюда, глохнет и теряет ориентацию.",
        "category": BuildingCategory.DEFENSIVE,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 50.0,
        "cost_material": 80.0,
        "construction_ticks": 1,
        "requires_workers": False,
        "resource_output_per_worker": {},
        "special_rules": "Акустический вакуум: снижает радиус обзора и дальность стратегического марша вражеских армий, находящихся в этой зоне.",
    },
    ElfsBuildingId.OBSERVATORY.value: {
        "id": ElfsBuildingId.OBSERVATORY.value,
        "faction_id": _FACTION,
        "name": "Обсерватория",
        "lore_description": "Оптические линзы, пронзающие слой стратосферного пепла. Позволяют эльфам видеть планы противника.",
        "category": BuildingCategory.DEFENSIVE,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 40.0,
        "cost_material": 100.0,
        "construction_ticks": 1,
        "requires_workers": False,
        "resource_output_per_worker": {},
        "special_rules": "Глаз Зенита: полностью снимает туман войны в огромном радиусе и дает 100% иммунитет к вражеским засадам в прилегающих нейтральных зонах.",
    },
}
