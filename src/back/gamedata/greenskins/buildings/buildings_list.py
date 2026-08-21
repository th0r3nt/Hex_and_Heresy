"""
Реестр зданий фракции зеленокожих.
Фокус на добыче провизии (грибы) и материалов (свалки), при этом золото добывается через воровство и барыг.
"""

from typing import Any

from src.back.l01_domain.factions.constants import BuildingCategory, ResourceType
from src.back.l01_domain.factions.models.buildings import BuildingUpgrade
from src.back.l01_domain.maps.constants import TerritoryZoneType
from src.back.gamedata.greenskins.common import GreenskinsBuildingId, GreenskinsUnitId

_FACTION = "greenskins"

BUILDINGS_LIST: dict[str, dict[str, Any]] = {
    # ==================================================================
    # ЭКОНОМИКА
    # ==================================================================
    GreenskinsBuildingId.MUSHROOM_CAVES.value: {
        "id": GreenskinsBuildingId.MUSHROOM_CAVES.value,
        "faction_id": _FACTION,
        "name": "Грибные пещеры",
        "lore_description": "Темные, влажные своды, где гоблины выращивают питательную (и слегка ядовитую) биомассу.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 0.0,
        "cost_material": 25.0,
        "construction_ticks": 1,
        "requires_workers": True,
        "resource_output_per_worker": {ResourceType.FOOD: 300.0},
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_grn_red_amanitas",
                name="Красные мухоморы",
                lore_description="Увеличивает добычу провизии, но иногда гоблины травятся и убивают друг друга.",
                cost_gold=10.0,
                cost_material=20.0,
            ),
            BuildingUpgrade(
                id="upg_grn_madness_brew",
                name="Варево безумия",
                lore_description="Позволяет варить зелья, дающие отрядам иммунитет к панике перед боем.",
                cost_gold=30.0,
                cost_material=30.0,
            ),
        ],
    },
    GreenskinsBuildingId.SCRAPYARD.value: {
        "id": GreenskinsBuildingId.SCRAPYARD.value,
        "faction_id": _FACTION,
        "name": "Свалка металлолома",
        "lore_description": "Орки не копают руду. Они стаскивают сюда ржавые телеги, куски доспехов и старое оружие для переплавки.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 0.0,
        "cost_material": 30.0,
        "construction_ticks": 1,
        "requires_workers": True,
        "resource_output_per_worker": {ResourceType.MATERIAL: 60.0},
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_grn_huge_magnet",
                name="Огромный магнит",
                lore_description="Гоблины сперли его у имперских инженеров. Пассивно притягивает больше лома.",
                cost_gold=50.0,
                cost_material=10.0,
            ),
        ],
    },
    GreenskinsBuildingId.HUCKSTER_CAMP.value: {
        "id": GreenskinsBuildingId.HUCKSTER_CAMP.value,
        "faction_id": _FACTION,
        "name": "Лагерь барыг",
        "lore_description": "Хитрые гоблины, готовые обменять старое барахло на блестящие монеты.",
        "category": BuildingCategory.ECONOMIC,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 50.0,
        "cost_material": 80.0,
        "construction_ticks": 2,
        "requires_workers": False,
        "resource_output_per_worker": {},
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_grn_thief_tunnels",
                name="Воровские туннели",
                lore_description="Пассивно ворует небольшой процент золота у соседних фракций.",
                cost_gold=100.0,
                cost_material=50.0,
            ),
        ],
    },
    # ==================================================================
    # ВОЕННАЯ ИНФРАСТРУКТУРА
    # ==================================================================
    GreenskinsBuildingId.FIGHTING_PITS.value: {
        "id": GreenskinsBuildingId.FIGHTING_PITS.value,
        "faction_id": _FACTION,
        "name": "Бойцовские ямы",
        "lore_description": "Место, где молодняк выбивает друг другу зубы, чтобы доказать право идти в набег.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 10.0,
        "cost_material": 50.0,
        "construction_ticks": 1,
        "unlock_tier": 1,
        "unlocked_unit_ids": [
            GreenskinsUnitId.YOUNG_ORCS_01.value,
            GreenskinsUnitId.ORC_TRICKSTERS_01.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_grn_bloody_sand",
                name="Кровавый песок",
                lore_description="В ямах выживают только самые жестокие. Дает бонус к базовому урону нанимаемой здесь пехоте.",
                cost_gold=20.0,
                cost_material=60.0,
            ),
        ],
    },
    GreenskinsBuildingId.IRONJAW_FORGE.value: {
        "id": GreenskinsBuildingId.IRONJAW_FORGE.value,
        "faction_id": _FACTION,
        "name": "Кузня Железнозубов",
        "lore_description": "Здесь с лязгом и вонью куют самое уродливое, но смертоносное оружие.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 30.0,
        "cost_material": 100.0,
        "construction_ticks": 2,
        "unlock_tier": 2,
        "unlocked_unit_ids": [
            GreenskinsUnitId.HARDENED_ORCS_02.value,
            GreenskinsUnitId.SHAMAN_APPRENTICES_02.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_grn_musket_assembly",
                name="Станция сборки мушкетов",
                lore_description="Разблокирует доступ к найму Банды снайперов.",
                cost_gold=80.0,
                cost_material=120.0,
            ),
        ],
    },
    GreenskinsBuildingId.OGRE_PIT.value: {
        "id": GreenskinsBuildingId.OGRE_PIT.value,
        "faction_id": _FACTION,
        "name": "Яма для огра",
        "lore_description": "Зловонная пещера, усеянная обглоданными костями. Здесь держат на цепи самых жутких тварей.",
        "category": BuildingCategory.MILITARY,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 80.0,
        "cost_material": 150.0,
        "construction_ticks": 3,
        "unlock_tier": 4,
        "unlocked_unit_ids": [
            GreenskinsUnitId.CAVE_OGRE_04.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_grn_raw_meat",
                name="Запасы сырого мяса",
                lore_description="Увеличивает пассивную регенерацию ХП огра во время боя.",
                cost_gold=50.0,
                cost_material=40.0,
            ),
        ],
    },
    # ==================================================================
    # КУЛЬТУРА И ОБОРОНА
    # ==================================================================
    GreenskinsBuildingId.CHIEFTAIN_IDOL.value: {
        "id": GreenskinsBuildingId.CHIEFTAIN_IDOL.value,
        "faction_id": _FACTION,
        "name": "Идол вождя",
        "lore_description": "Куча мусора, щебня и черепов, отдаленно напоминающая рожу самого вождя.",
        "category": BuildingCategory.UNIQUE,
        "allowed_zone": TerritoryZoneType.BASE,
        "cost_gold": 100.0,
        "cost_material": 200.0,
        "construction_ticks": 3,
        "unlock_tier": 3,
        "unlocked_unit_ids": [
            GreenskinsUnitId.IRONJAWS_03.value,
        ],
        "available_upgrades": [
            BuildingUpgrade(
                id="upg_grn_loud_chants",
                name="Громкие песнопения",
                lore_description="Усиливает множитель урона от механики 'Зеленой волны' при массовой атаке.",
                cost_gold=120.0,
                cost_material=80.0,
            ),
        ],
    },
    GreenskinsBuildingId.FEAR_TOTEM.value: {
        "id": GreenskinsBuildingId.FEAR_TOTEM.value,
        "faction_id": _FACTION,
        "name": "Тотем устрашения",
        "lore_description": "Насаженные на колья тела врагов. Орки не любят наблюдать за границей, они любят отпугивать.",
        "category": BuildingCategory.DEFENSIVE,
        "allowed_zone": TerritoryZoneType.ALLIED_LANDS,
        "cost_gold": 10.0,
        "cost_material": 30.0,
        "construction_ticks": 1,
        "requires_workers": False,
        "resource_output_per_worker": {},
        "special_rules": "Вместо вскрытия Тумана войны накладывает штраф (-1 к инициативе) на любые вражеские отряды, вторгающиеся в эту зону.",
    },
}
