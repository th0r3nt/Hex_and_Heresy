"""
Реестр зданий фракции 'Паства метеорита'.
Ориентированы на переработку тел, жертвоприношения и магические ритуалы призыва.
"""

from typing import Any

from src.back.l01_domain.factions.constants import BuildingCategory, ResourceType
from src.back.l01_domain.factions.models.buildings import BuildingUpgrade
from src.back.l01_domain.maps.constants import TerritoryZoneType
from src.back.gamedata.congregation_of_the_meteorite.common import CotmBuildingId, CotmUnitId

_FACTION = "congregation_of_the_meteorite"

BUILDINGS_LIST: dict[str, dict[str, Any]] = {
    # ==================================================================
    # УНИКАЛЬНАЯ ОБОРОНА И БАЗА
    # ==================================================================
    CotmBuildingId.PROGENITOR_ALTAR.value: {
        "id": CotmBuildingId.PROGENITOR_ALTAR.value,
        "faction_id": _FACTION,
        "name": "Алтарь Прародителя",
        "lore_description": "Центральный обелиск из резонита. Пульсирует во тьме, требуя крови.",
        "category": BuildingCategory.DEFENSIVE,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 50.0,
        "cost_material": 100.0,
        "construction_ticks": 2,
        "requires_workers": False,
        "resource_output_per_worker": {},
        "unlock_tier": 0,
        "unlocked_unit_ids": [],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_cotm_blood_sacrifice",
                name="Кровавая жертва",
                lore_description="Разрешает уничтожать собственные отряды рабов для получения ресурсов.",
                cost_gold=30.0,
                cost_material=50.0,
            ),
            BuildingUpgrade(
                id="upg_cotm_aura_of_madness",
                name="Аура безумия",
                lore_description="Враги, подошедшие к Алтарю, начинают слышать голоса.",
                cost_gold=60.0,
                cost_material=100.0,
            ),
            BuildingUpgrade(
                id="upg_cotm_soul_magnet",
                name="Магнит душ",
                lore_description="Увеличивает процент сохраняемой вражеской экипировки на любом поле брани.",
                cost_gold=100.0,
                cost_material=150.0,
            ),
        ],
        "special_rules": "Кровавая жертва: конвертирует ХП отряда в золото и материалы. Аура безумия: накладывает сильный дебафф морали на врагов на гексе базы.",
    },
    # ==================================================================
    # ЭКОНОМИКА И ДОБЫЧА
    # ==================================================================
    CotmBuildingId.LOOTER_CAMP.value: {
        "id": CotmBuildingId.LOOTER_CAMP.value,
        "faction_id": _FACTION,
        "name": "Лагерь мародеров",
        "lore_description": "Основной источник золота. Члены Паствы приносят сюда кольца, срезанные с мертвецов.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 10.0,
        "cost_material": 30.0,
        "construction_ticks": 1,
        "requires_workers": True,
        "resource_output_per_worker": {ResourceType.GOLD: 80.0},
        "unlock_tier": 0,
        "unlocked_unit_ids": [
            CotmUnitId.GOBLIN_LOOTERS_00.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_cotm_black_market",
                name="Черный рынок",
                lore_description="Позволяет менять материалы (кости и ржавчину) на золото.",
                cost_gold=40.0,
                cost_material=20.0,
            ),
            BuildingUpgrade(
                id="upg_cotm_slave_pens",
                name="Загоны для рабов",
                lore_description="Увеличивает добычу золота на 20%, но каждый такт есть 10% шанс спавна враждебного отряда бунтовщиков.",
                cost_gold=60.0,
                cost_material=60.0,
            ),
        ],
    },
    CotmBuildingId.BONE_PIT.value: {
        "id": CotmBuildingId.BONE_PIT.value,
        "faction_id": _FACTION,
        "name": "Костяная яма",
        "lore_description": "Огромный карьер, куда сбрасывают трупы. Здесь добывают кости и ржавчину — строительный материал Паствы.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 0.0,
        "cost_material": 20.0,
        "construction_ticks": 1,
        "requires_workers": True,
        "resource_output_per_worker": {ResourceType.MATERIAL: 100.0},
        "unlock_tier": 0,
        "unlocked_unit_ids": [
            CotmUnitId.NECROMANCERS_00.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_cotm_blood_mill",
                name="Кровавая мельница",
                lore_description="Пассивно увеличивает прирост материалов на 30%.",
                cost_gold=30.0,
                cost_material=40.0,
            ),
            BuildingUpgrade(
                id="upg_cotm_petrification_ritual",
                name="Ритуал окаменения",
                lore_description="Все союзные отряды нежити (зомби, мумии) навсегда получают +1 к броне при найме.",
                cost_gold=80.0,
                cost_material=100.0,
            ),
        ],
    },
    CotmBuildingId.SLAUGHTERHOUSE.value: {
        "id": CotmBuildingId.SLAUGHTERHOUSE.value,
        "faction_id": _FACTION,
        "name": "Бойня",
        "lore_description": "Заменяет классические фермы. Здесь разделывают все, что можно съесть, невзирая на расу.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 10.0,
        "cost_material": 30.0,
        "construction_ticks": 1,
        "requires_workers": True,
        "resource_output_per_worker": {ResourceType.FOOD: 200.0},
        "unlock_tier": 0,
        "unlocked_unit_ids": [],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_cotm_cannibalism",
                name="Каннибализм",
                lore_description="Если в бою на территории базы убит живой вражеский отряд, Бойня генерирует бонусную провизию.",
                cost_gold=20.0,
                cost_material=40.0,
            ),
            BuildingUpgrade(
                id="upg_cotm_mutagen_vat",
                name="Чан с мутагеном",
                lore_description="Позволяет тратить провизию перед боем, чтобы дать отряду +30% к урону ценой потери ХП каждый ход.",
                cost_gold=50.0,
                cost_material=60.0,
            ),
        ],
    },
    # ==================================================================
    # ВОЕННАЯ ИНФРАСТРУКТУРА
    # ==================================================================
    CotmBuildingId.DESECRATED_CHURCHYARD.value: {
        "id": CotmBuildingId.DESECRATED_CHURCHYARD.value,
        "faction_id": _FACTION,
        "name": "Оскверненный погост",
        "lore_description": "Земля, пропитанная магией некроза. Здесь поднимают базовую нежить и призывают низших демонов.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 20.0,
        "cost_material": 80.0,
        "construction_ticks": 1,
        "unlock_tier": 1,
        "unlocked_unit_ids": [
            CotmUnitId.ZOMBIE_HORDE_01.value,
            CotmUnitId.LESSER_DEMONS_01.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_cotm_fresh_corpses",
                name="Свежие трупы",
                lore_description="Ускоряет наем нежити в 1.5 раза.",
                cost_gold=30.0,
                cost_material=50.0,
            ),
            BuildingUpgrade(
                id="upg_cotm_plague_vapors",
                name="Чумные испарения",
                lore_description="Зомби получают ауру гниения, наносящую пассивный урон в ближнем бою.",
                cost_gold=60.0,
                cost_material=80.0,
            ),
        ],
    },
    CotmBuildingId.ARENA_OF_PAIN.value: {
        "id": CotmBuildingId.ARENA_OF_PAIN.value,
        "faction_id": _FACTION,
        "name": "Арена боли",
        "lore_description": "Место, где выживают только самые жестокие орки и бывшие имперские рыцари.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 50.0,
        "cost_material": 100.0,
        "construction_ticks": 2,
        "unlock_tier": 2,
        "unlocked_unit_ids": [
            CotmUnitId.ORC_GLADIATORS_02.value,
            CotmUnitId.DARK_MEN_AT_ARMS_02.value,
            CotmUnitId.GHOSTS_02.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_cotm_vampirism",
                name="Вампиризм",
                lore_description="Темные латники восстанавливают на 25% больше здоровья при убийстве врага.",
                cost_gold=80.0,
                cost_material=100.0,
            ),
            BuildingUpgrade(
                id="upg_cotm_ectoplasm",
                name="Эктоплазма",
                lore_description="Шанс уклонения Призраков от физических атак увеличивается с 50% до 60%.",
                cost_gold=100.0,
                cost_material=120.0,
            ),
        ],
    },
    CotmBuildingId.SUMMONING_CIRCLE.value: {
        "id": CotmBuildingId.SUMMONING_CIRCLE.value,
        "faction_id": _FACTION,
        "name": "Круг призыва",
        "lore_description": "Площадка с рунами из свежей крови для призыва и трансформации элитных мутантов.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 100.0,
        "cost_material": 150.0,
        "construction_ticks": 2,
        "unlock_tier": 3,
        "unlocked_unit_ids": [
            CotmUnitId.WEREWOLVES_03.value,
            CotmUnitId.ELF_BLOODLETTERS_03.value,
            CotmUnitId.BLOODLETTING_MAGE_03.value,
            CotmUnitId.BOMBERS_03.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_cotm_lunar_prism",
                name="Лунная призма",
                lore_description="Оборотни могут трансформироваться в волков даже оставаясь на гексе базы.",
                cost_gold=120.0,
                cost_material=150.0,
            ),
        ],
    },
    CotmBuildingId.TOMB_OF_THE_FORGOTTEN.value: {
        "id": CotmBuildingId.TOMB_OF_THE_FORGOTTEN.value,
        "faction_id": _FACTION,
        "name": "Гробница забытых",
        "lore_description": "Черный зиккурат, таящий в себе ультимативные кошмары забытых эпох.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 200.0,
        "cost_material": 300.0,
        "construction_ticks": 3,
        "unlock_tier": 4,
        "unlocked_unit_ids": [
            CotmUnitId.MUMMY_SUMMONERS_04.value,
            CotmUnitId.GREEDY_DRAGON_05.value,
            CotmUnitId.IMMORTAL_RIDERS_05.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_cotm_riders_crypt",
                name="Склеп всадников",
                lore_description="Сокращает время бесплатного воскрешения Бессмертных всадников с 3 тактов до 2.",
                cost_gold=150.0,
                cost_material=200.0,
            ),
            BuildingUpgrade(
                id="upg_cotm_golden_tribute",
                name="Золотые подношения",
                lore_description="Снижает астрономическую стоимость найма Алчного дракона на 15%.",
                cost_gold=250.0,
                cost_material=100.0,
            ),
        ],
    },
    # ==================================================================
    # УНИКАЛЬНАЯ АРХИТЕКТУРА
    # ==================================================================
    CotmBuildingId.GATES_OF_THE_ABYSS.value: {
        "id": CotmBuildingId.GATES_OF_THE_ABYSS.value,
        "faction_id": _FACTION,
        "name": "Врата Бездны",
        "lore_description": "Абсолютная аннигиляция. Огромный портал, разрывающий ткань реальности.",
        "category": BuildingCategory.UNIQUE,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 500.0,
        "cost_material": 1000.0,
        "construction_ticks": 4,
        "requires_workers": False,
        "resource_output_per_worker": {},
        "unlock_tier": 6,
        "unlocked_unit_ids": [
            CotmUnitId.DOOM_HARBINGERS_06.value,
        ],
        "available_upgrades": [],
        "special_rules": "Таймер судного дня: после постройки Врата постоянно потребляют материалы и золото. Если ресурсы кончаются, здание рушится, уничтожая половину рабочих на базе.",
    },
}
