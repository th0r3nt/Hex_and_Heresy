"""
Реестр зданий фракции баронских войск.
Фокус на абсолютной обороне, рэкете, выкупах и сборе пошлин.
"""

from typing import Any

from src.back.l01_domain.factions.constants import BuildingCategory, ResourceType
from src.back.l01_domain.factions.models.buildings import BuildingUpgrade
from src.back.l01_domain.maps.constants import TerritoryZoneType
from src.back.gamedata.baronial_troops.common import BaronialBuildingId, BaronialUnitId

_FACTION = "baronial_troops"

BUILDINGS_LIST: dict[str, dict[str, Any]] = {
    # ==================================================================
    # УНИКАЛЬНАЯ ОБОРОНА И БАЗА
    # ==================================================================
    BaronialBuildingId.BARONS_CASTLE.value: {
        "id": BaronialBuildingId.BARONS_CASTLE.value,
        "faction_id": _FACTION,
        "name": "Замок Барона",
        "lore_description": "Толстые стены, глубокий ров и сотни заряженных арбалетов. Если замок падет, победитель получит всю накопившуюся в подвалах казну.",
        "category": BuildingCategory.DEFENSIVE,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 100.0,
        "cost_material": 200.0,
        "construction_ticks": 2,
        "requires_workers": False,
        "resource_output_per_worker": {},
        "unlock_tier": 0,
        "unlocked_unit_ids": [],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_bar_boiling_oil",
                name="Кипящее масло",
                lore_description="Ужасающая защита против тех, кто посмеет подойти к воротам.",
                cost_gold=50.0,
                cost_material=30.0,
            ),
            BuildingUpgrade(
                id="upg_bar_deep_moat",
                name="Глубокий ров",
                lore_description="Конница и тяжелая пехота врага теряют свои бонусы натиска при атаке на замок.",
                cost_gold=80.0,
                cost_material=100.0,
            ),
            BuildingUpgrade(
                id="upg_bar_golden_carriage",
                name="Золоченая карета",
                lore_description="Барон готовится лично выехать на поле боя... в бронированной передвижной крепости.",
                cost_gold=250.0,
                cost_material=200.0,
            ),
        ],
        "special_rules": "Кипящее масло: наносит колоссальный урон первым двум отрядам ближнего боя, атакующим гекс базы, до начала фазы боя. Золоченая карета разблокирует найм 'Кареты Барона' (Тир 6).",
    },
    # ==================================================================
    # ЭКОНОМИКА И КОНТРОЛЬ
    # ==================================================================
    BaronialBuildingId.OPPRESSED_VILLAGE.value: {
        "id": BaronialBuildingId.OPPRESSED_VILLAGE.value,
        "faction_id": _FACTION,
        "name": "Угнетенная деревня",
        "lore_description": "Источник еды и пушечного мяса. Местные живут в постоянном страхе перед сборщиками податей.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 0.0,
        "cost_material": 30.0,
        "construction_ticks": 1,
        "requires_workers": True,
        "resource_output_per_worker": {ResourceType.FOOD: 200.0},
        "unlock_tier": 0,
        "unlocked_unit_ids": [
            BaronialUnitId.SERFS_MOB_00.value,
        ],
        "available_upgrades": [],
    },
    BaronialBuildingId.ROADSIDE_OUTPOST.value: {
        "id": BaronialBuildingId.ROADSIDE_OUTPOST.value,
        "faction_id": _FACTION,
        "name": "Дорожная застава",
        "lore_description": "Здание-рэкетир на пересечении трактов. Любой проходящий мимо обязан платить.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 20.0,
        "cost_material": 50.0,
        "construction_ticks": 1,
        "requires_workers": True,
        "resource_output_per_worker": {ResourceType.GOLD: 80.0},
        "unlock_tier": 0,
        "unlocked_unit_ids": [
            BaronialUnitId.TAX_COLLECTORS_00.value,
        ],
        "available_upgrades": [],
        "special_rules": "Рэкет: любой нейтральный или вражеский отряд, проходящий через прилегающие к заставе гексы, обязан заплатить пошлину золотом, иначе Баронство получает легитимный повод для войны (Casus Belli).",
    },
    BaronialBuildingId.RUSTY_PITS.value: {
        "id": BaronialBuildingId.RUSTY_PITS.value,
        "faction_id": _FACTION,
        "name": "Ржавые ямы",
        "lore_description": "Открытые разрезы в отвалах старой войны. Крепостные выламывают из глины проржавевшие лафеты, ядра и остовы обозов - барон платит за железо телами.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 0.0,
        "cost_material": 35.0,
        "construction_ticks": 1,
        "requires_workers": True,
        "resource_output_per_worker": {ResourceType.MATERIAL: 60.0},
        "unlock_tier": 0,
        "unlocked_unit_ids": [],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_bar_debt_labor",
                name="Долговая отработка",
                lore_description="Должников из тюрьмы гонят на разрез. Работают они бесплатно и недолго.",
                cost_gold=40.0,
                cost_material=20.0,
            ),
        ],
        "special_rules": "Долговая отработка: увеличивает добычу материала, но каждый такт есть небольшой шанс потерять часть отряда рабочих от обвала и болезней.",
    },
    BaronialBuildingId.DEBTORS_PRISON.value: {
        "id": BaronialBuildingId.DEBTORS_PRISON.value,
        "faction_id": _FACTION,
        "name": "Долговая тюрьма",
        "lore_description": "Сырые камеры, где сидят те, кто не смог оплатить налог на жизнь в Баронстве.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 80.0,
        "cost_material": 120.0,
        "construction_ticks": 2,
        "requires_workers": False,
        "resource_output_per_worker": {},
        "available_upgrades": [],
        "special_rules": "Выкуп: позволяет брать пленных после победных боев на своей территории. Игрок может требовать за них выкуп у других фракций (в дипломатических письмах). При отказе пленные превращаются в бесплатных рабочих.",
    },
    # ==================================================================
    # ВОЕННАЯ ИНФРАСТРУКТУРА
    # ==================================================================
    BaronialBuildingId.WATCHTOWERS.value: {
        "id": BaronialBuildingId.WATCHTOWERS.value,
        "faction_id": _FACTION,
        "name": "Сторожевые вышки",
        "lore_description": "Высокие деревянные конструкции. Сигнальные костры видно за многие мили.",
        "category": BuildingCategory.DEFENSIVE,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 10.0,
        "cost_material": 25.0,
        "construction_ticks": 1,
        "unlock_tier": 0,
        "unlocked_unit_ids": [
            BaronialUnitId.SIGNALMEN_00.value,
        ],
        "available_upgrades": [],
        "special_rules": "Информационный брокер: позволяет видеть состав проходящих армий в радиусе 2 гексов и продавать эту информацию другим фракциям.",
    },
    BaronialBuildingId.GARRISON_COURTYARD.value: {
        "id": BaronialBuildingId.GARRISON_COURTYARD.value,
        "faction_id": _FACTION,
        "name": "Внутренний двор гарнизона",
        "lore_description": "Здесь тренируются гвардейцы и заключают контракты ветераны-наемники.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 40.0,
        "cost_material": 80.0,
        "construction_ticks": 1,
        "unlock_tier": 1,
        "unlocked_unit_ids": [
            BaronialUnitId.CASTLE_GUARDS_01.value,
            BaronialUnitId.OUTPOST_SHOOTERS_01.value,
            BaronialUnitId.VETERAN_MERCENARIES_02.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_bar_elite_pavises",
                name="Элитные павезы",
                lore_description="Улучшает щиты арбалетчиков. Штурмовать их под градом болтов становится самоубийством.",
                cost_gold=40.0,
                cost_material=60.0,
            ),
            BuildingUpgrade(
                id="upg_bar_imperial_deserters",
                name="Имперские дезертиры",
                lore_description="Баронство начинает скупать предателей из Ордена.",
                cost_gold=120.0,
                cost_material=80.0,
            ),
        ],
        "special_rules": "Элитные павезы позволяют карточкам с павезами игнорировать не одну, а две первые дальние атаки. Имперские дезертиры разблокируют найм Рыцарей-дезертиров (Тир 5).",
    },
    BaronialBuildingId.WAGON_SHED.value: {
        "id": BaronialBuildingId.WAGON_SHED.value,
        "faction_id": _FACTION,
        "name": "Обозный сарай",
        "lore_description": "Склады с припасами, золотом и элем. Сердце логистики баронства.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 30.0,
        "cost_material": 60.0,
        "construction_ticks": 1,
        "unlock_tier": 2,
        "unlocked_unit_ids": [
            BaronialUnitId.SUPPLY_WAGON_02.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_bar_armored_wagons",
                name="Бронированные кареты",
                lore_description="Сборщики податей получают шанс сбежать при нападении, сохранив золото.",
                cost_gold=30.0,
                cost_material=40.0,
            ),
            BuildingUpgrade(
                id="upg_bar_poisoned_wells",
                name="Отравленные колодцы",
                lore_description="Если мы не сможем это съесть, никто не сможет.",
                cost_gold=20.0,
                cost_material=20.0,
            ),
        ],
        "special_rules": "Отравленные колодцы: если враг разрушает Обозный сарай или захватывает базу, вся вражеская армия в этой зоне лишается провизии на 2 такта (мгновенное дезертирство).",
    },
    BaronialBuildingId.EXECUTION_SQUARE.value: {
        "id": BaronialBuildingId.EXECUTION_SQUARE.value,
        "faction_id": _FACTION,
        "name": "Площадь казней",
        "lore_description": "Мрачное место в центре Замка, пропитанное кровью. Здесь обитает гильдия Палачей.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 80.0,
        "cost_material": 60.0,
        "construction_ticks": 2,
        "unlock_tier": 3,
        "unlocked_unit_ids": [
            BaronialUnitId.EXECUTIONERS_03.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_bar_gallows_of_fear",
                name="Виселицы для устрашения",
                lore_description="Лес из повешенных трупов на границах баронства.",
                cost_gold=40.0,
                cost_material=60.0,
            ),
        ],
        "special_rules": "Виселицы: механика 'Страха' от Палачей начинает действовать даже на элитные отряды, а мораль собственных крестьян повышается (они боятся Палача больше, чем врага).",
    },
    BaronialBuildingId.MENAGERIE.value: {
        "id": BaronialBuildingId.MENAGERIE.value,
        "faction_id": _FACTION,
        "name": "Зверинец",
        "lore_description": "Огромные железные клетки, куда кидают пойманых мутантов и огров.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 100.0,
        "cost_material": 120.0,
        "construction_ticks": 3,
        "unlock_tier": 4,
        "unlocked_unit_ids": [
            BaronialUnitId.TAME_OGRE_04.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_bar_steel_plating",
                name="Стальные пластины",
                lore_description="Кузнецы зашивают огров в дополнительные листы корабельной стали.",
                cost_gold=60.0,
                cost_material=80.0,
            ),
        ],
    },
}
