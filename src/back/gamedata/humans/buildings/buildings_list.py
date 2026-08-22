"""
Реестр зданий фракции людей.
Включает экономические, военные и уникальные строения, а также их улучшения.
"""

from typing import Any

from src.back.l01_domain.factions.constants import BuildingCategory, ResourceType
from src.back.l01_domain.factions.models.buildings import BuildingUpgrade
from src.back.l01_domain.maps.constants import TerritoryZoneType
from src.back.gamedata.humans.common import HumanBuildingId, HumanUnitId

_FACTION = "humans"

BUILDINGS_LIST: dict[str, dict[str, Any]] = {
    # ==================================================================
    # ЭКОНОМИКА
    # ==================================================================
    HumanBuildingId.WHEAT_FIELDS.value: {
        "id": HumanBuildingId.WHEAT_FIELDS.value,
        "faction_id": _FACTION,
        "name": "Пшеничные угодья",
        "lore_description": "Кровь в земле, хлеб на столе. Основной источник провизии для армий Империи.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 0.0,
        "cost_material": 40.0,
        "construction_ticks": 1,
        "requires_workers": True,
        "resource_output_per_worker": {ResourceType.FOOD: 250.0},
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_hum_draft_horses",
                name="Тягловые лошади",
                lore_description="Наконец-то настоящие мускулы. Увеличивает добычу провизии.",
                cost_gold=30.0,
                cost_material=20.0,
            ),
            BuildingUpgrade(
                id="upg_hum_fortified_barns",
                name="Скрытые припасы",
                lore_description="Заприте зерно. Пусть враг голодает.",
                cost_gold=15.0,
                cost_material=50.0,
            ),
        ],
        "special_rules": "Скрытые припасы: если враг захватывает эту зону, он не может украсть накопленные запасы еды.",
    },
    HumanBuildingId.QUARRY.value: {
        "id": HumanBuildingId.QUARRY.value,
        "faction_id": _FACTION,
        "name": "Каменоломня",
        "lore_description": "Бейте в землю! Лорду нужны новые стены.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 0.0,
        "cost_material": 40.0,
        "construction_ticks": 1,
        "requires_workers": True,
        "resource_output_per_worker": {ResourceType.MATERIAL: 50.0},
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_hum_deep_mines",
                name="Глубинные шахты",
                lore_description="Копайте глубже! Не обращайте внимания на дрожь земли.",
                cost_gold=50.0,
                cost_material=20.0,
            ),
        ],
        "special_rules": "Глубинные шахты: дает бонус к материалам, но каждый ход есть 5% шанс обвала.",
    },
    HumanBuildingId.TRADING_GUILD.value: {
        "id": HumanBuildingId.TRADING_GUILD.value,
        "faction_id": _FACTION,
        "name": "Торговая гильдия",
        "lore_description": "Золото - это истинная кровь Империи.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 100.0,
        "cost_material": 100.0,
        "construction_ticks": 2,
        "requires_workers": False,  # Пассивный доход
        "resource_output_per_worker": {},
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_hum_smuggler_routes",
                name="Контрабандные тропы",
                lore_description="Мы не спрашиваем, откуда это, только сколько это стоит.",
                cost_gold=80.0,
                cost_material=20.0,
            ),
        ],
        "special_rules": "Торговая гильдия пассивно меняет излишки провизии на золото. Контрабандные тропы снижают стоимость найма наемников на 20%.",
    },
    # ==================================================================
    # ВОЕННАЯ ИНФРАСТРУКТУРА
    # ==================================================================
    HumanBuildingId.CITY_BARRACKS.value: {
        "id": HumanBuildingId.CITY_BARRACKS.value,
        "faction_id": _FACTION,
        "name": "Городские казармы",
        "lore_description": "Превратите этих деревенских парней в убийц.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 20.0,
        "cost_material": 60.0,
        "construction_ticks": 1,
        "unlock_tier": 1,
        "unlocked_unit_ids": [
            HumanUnitId.CITY_GUARD_01.value,
            HumanUnitId.MILITIA_00.value,
            HumanUnitId.HUNTERS_WITH_DOGS_01.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_hum_training_ground",
                name="Тренировочный плац",
                lore_description="Пот экономит кровь!",
                cost_gold=40.0,
                cost_material=40.0,
            ),
        ],
        "special_rules": "Тренировочный плац дает постоянный +1 к броне для нанятых здесь юнитов ближнего боя.",
    },
    HumanBuildingId.WEAPONS_MANUFACTORY.value: {
        "id": HumanBuildingId.WEAPONS_MANUFACTORY.value,
        "faction_id": _FACTION,
        "name": "Оружейная мануфактура",
        "lore_description": "Сладкий звук прогресса... и пороха.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 60.0,
        "cost_material": 120.0,
        "construction_ticks": 2,
        "unlock_tier": 2,
        "unlocked_unit_ids": [
            HumanUnitId.IRONSIDES_02.value,
            HumanUnitId.SHOOTERS_02.value,
            HumanUnitId.WAR_VETERANS_03.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_hum_blast_furnace",
                name="Доменная печь",
                lore_description="Раздувайте огонь! Нам нужно больше стали.",
                cost_gold=100.0,
                cost_material=50.0,
            ),
            BuildingUpgrade(
                id="upg_hum_rifled_barrels",
                name="Нарезные стволы",
                lore_description="Точность смертоносна.",
                cost_gold=150.0,
                cost_material=80.0,
            ),
        ],
        "special_rules": "Доменная печь снижает стоимость найма бронированной пехоты. Нарезные стволы дают аркебузирам 15% шанс нанести двойной урон сквозь броню.",
    },
    HumanBuildingId.ROYAL_STABLES.value: {
        "id": HumanBuildingId.ROYAL_STABLES.value,
        "faction_id": _FACTION,
        "name": "Королевские конюшни",
        "lore_description": "Готовьте седла. Охота начинается.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 100.0,
        "cost_material": 120.0,
        "construction_ticks": 2,
        "unlock_tier": 2,
        "unlocked_unit_ids": [
            HumanUnitId.LIGHT_CAVALRY_02.value,
            HumanUnitId.KNIGHTS_04.value,  # Нанимаются только после улучшения
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_hum_draft_horse_breeding",
                name="Разведение тяжеловозов",
                lore_description="Только самые сильные звери для Ордена.",
                cost_gold=200.0,
                cost_material=100.0,
            ),
            BuildingUpgrade(
                id="upg_hum_spiked_horseshoes",
                name="Подковы с шипами",
                lore_description="Пусть они растопчут этот мусор.",
                cost_gold=50.0,
                cost_material=50.0,
            ),
        ],
        "special_rules": "Разведение тяжеловозов разблокирует возможность найма Орденских рыцарей. Подковы усиливают первый натиск любой кавалерии.",
    },
    HumanBuildingId.MEDICAL_TENT.value: {
        "id": HumanBuildingId.MEDICAL_TENT.value,
        "faction_id": _FACTION,
        "name": "Медицинский шатер",
        "lore_description": "Несите бинты и костяные пилы.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 50.0,
        "cost_material": 30.0,
        "construction_ticks": 1,
        "unlock_tier": 2,
        "unlocked_unit_ids": [
            HumanUnitId.FIELD_HOSPITAL_02.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_hum_alchemical_potions",
                name="Алхимические зелья",
                lore_description="Пей. Ты либо исцелишься, либо растворишься.",
                cost_gold=100.0,
                cost_material=20.0,
            ),
        ],
        "special_rules": "Алхимические зелья увеличивают процент воскрешенных солдат с 10% до 15%.",
    },
    # ==================================================================
    # РЕЛИГИЯ И КОНТРОЛЬ
    # ==================================================================
    HumanBuildingId.CHAPEL_OF_LIGHT.value: {
        "id": HumanBuildingId.CHAPEL_OF_LIGHT.value,
        "faction_id": _FACTION,
        "name": "Часовня Света",
        "lore_description": "Свет защищает всех нас.",
        "category": BuildingCategory.UNIQUE,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 150.0,
        "cost_material": 200.0,
        "construction_ticks": 3,
        "unlock_tier": 3,
        "unlocked_unit_ids": [
            HumanUnitId.REPENTANT_SINNERS_00.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_hum_sale_of_indulgences",
                name="Продажа индульгенций",
                lore_description="У спасения есть цена, и мы принимаем золото.",
                cost_gold=50.0,
                cost_material=10.0,
            ),
            BuildingUpgrade(
                id="upg_hum_saints_reliquary",
                name="Реликварий святого",
                lore_description="Во имя Его, мы не ведаем страха.",
                cost_gold=250.0,
                cost_material=50.0,
            ),
        ],
        "special_rules": "Продажа индульгенций позволяет напрямую конвертировать золото в Очки Веры. Реликварий делает гарнизон невосприимчивым к аурам страха.",
    },
    HumanBuildingId.INQUISITION_HALL.value: {
        "id": HumanBuildingId.INQUISITION_HALL.value,
        "faction_id": _FACTION,
        "name": "Зал Инквизиции",
        "lore_description": "Никакая ересь не скроется от нашего взора.",
        "category": BuildingCategory.UNIQUE,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 300.0,
        "cost_material": 400.0,
        "construction_ticks": 4,
        "unlock_tier": 4,
        "unlocked_unit_ids": [
            HumanUnitId.WITCH_HUNTERS_03.value,
            HumanUnitId.INQUISITION_MAGISTERS_05.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_hum_torture_instruments",
                name="Пыточные инструменты",
                lore_description="У каждого есть секреты. У нас есть щипцы.",
                cost_gold=100.0,
                cost_material=50.0,
            ),
        ],
        "special_rules": "Пыточные инструменты: при допросе пленных гарантированно выбивается информация о текущем найме войск врага.",
    },
    # ==================================================================
    # ОБОРОНА
    # ==================================================================
    HumanBuildingId.WATCHTOWER.value: {
        "id": HumanBuildingId.WATCHTOWER.value,
        "faction_id": _FACTION,
        "name": "Смотровая вышка",
        "lore_description": "Глаза открыты! Они уже близко.",
        "category": BuildingCategory.DEFENSIVE,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 10.0,
        "cost_material": 20.0,
        "construction_ticks": 1,
        "requires_workers": False,
        "resource_output_per_worker": {},
        "special_rules": "Снимает Туман войны с прилегающих Ничейных земель. Очень низкий запас прочности.",
    },
}
