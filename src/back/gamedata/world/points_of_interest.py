"""
Реестр точек интереса Ничьей земли.

Лорные ориентиры (is_landmark=True) уникальны и описаны в
docs/lore/geography/no_mans_land/famous_places.md - генератор мира ставит
каждый ровно один раз в экваториальном поясе. Процедурные места
размножаются свободно по нейтральным гексам.

Про резонит: отдельного ресурса под него нет - для эльфов, Паствы и
зеленокожих это разновидность материала. Люди и баронства резонит не
используют вовсе, поэтому их расовый множитель на таких местах равен нулю.
"""

from typing import Any

from src.back.gamedata.world.common import PointOfInterestId
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.world.models.points_of_interest import PointOfInterestCategory

POINTS_OF_INTEREST_LIST: dict[str, dict[str, Any]] = {
    # ==================================================================
    # ЛОРНЫЕ ОРИЕНТИРЫ ЭКВАТОРИАЛЬНОГО ПОЯСА
    # ==================================================================
    PointOfInterestId.RUSTY_SWORDS_VALLEY.value: {
        "id": PointOfInterestId.RUSTY_SWORDS_VALLEY.value,
        "name": "Долина ржавых мечей",
        "category": PointOfInterestCategory.BATTLEFIELD,
        "is_landmark": True,
        "lore_description": (
            "Здесь двести лет назад Девятый имперский легион попал в засаду объединенных "
            "орочьих племен и был вырезан до последнего человека. Квадратные мили земли "
            "усеяны полусгнившими кирасами, костями и торчащими из земли пиками; от обилия "
            "крови и ржавеющего железа флора приобрела бурый оттенок."
        ),
        "yield_multipliers": {
            ResourceType.MATERIAL: 2.5,  # Гигантский запас металлолома для переплавки
            ResourceType.GOLD: 1.2,
        },
        "race_yield_multipliers": {
            # Паства выгребает отсюда не железо, а кости для некромантии
            FactionRace.CONGREGATION_OF_THE_METEORITE: 1.4,
            FactionRace.GREENSKINS: 1.2,
        },
        "morale_penalty_races": [FactionRace.HUMANS],  # Копаться в костях своего легиона
    },
    PointOfInterestId.RADIANCE_CRATER.value: {
        "id": PointOfInterestId.RADIANCE_CRATER.value,
        "name": "Кратер сияния",
        "category": PointOfInterestCategory.GEO_ANOMALY,
        "is_landmark": True,
        "lore_description": (
            "Эпицентр прямого удара крупного осколка Прародителя: горная гряда расплавилась "
            "в кратер из зеленого бритвенно-острого стекла. Гравитация нестабильна, оплавленные "
            "обломки дрейфуют в воздухе, а ночью кратер испускает ядовитое неоновое свечение. "
            "Священная земля для эльфов и смертельная ловушка для всех остальных."
        ),
        "yield_multipliers": {
            ResourceType.MATERIAL: 3.0,  # Максимальная концентрация остаточного резонита
        },
        "race_yield_multipliers": {
            FactionRace.ELFS: 1.3,
            FactionRace.CONGREGATION_OF_THE_METEORITE: 1.0,
            FactionRace.GREENSKINS: 0.8,
            FactionRace.HUMANS: 0.0,  # Чистый геном тут просто закипает
            FactionRace.BARONIAL_TROOPS: 0.0,
            FactionRace.MERCENARIES: 0.0,
        },
        "morale_penalty_races": [FactionRace.HUMANS, FactionRace.BARONIAL_TROOPS],
    },
    PointOfInterestId.OLD_STADT.value: {
        "id": PointOfInterestId.OLD_STADT.value,
        "name": "Олд-Штадт",
        "category": PointOfInterestCategory.RUINS,
        "is_landmark": True,
        "lore_description": (
            "Провалившийся под землю мегаполис людей эпохи до Катаклизма. Над токсичной "
            "трясиной торчат только черные готические шпили соборов и крыши высочайших башен, "
            "между которыми мародеры проложили шаткие мостки. В мутной воде прячутся низшие "
            "демоны и мутировавшие земноводные, охотящиеся на разведчиков."
        ),
        "yield_multipliers": {
            ResourceType.MATERIAL: 1.8,  # Чертежи древних механизмов
            ResourceType.GOLD: 2.0,
        },
        "race_yield_multipliers": {
            FactionRace.HUMANS: 1.2,  # Свою же архитектуру они читают лучше прочих
        },
        "morale_penalty_races": [],
    },
    PointOfInterestId.SORROW_LOWLAND.value: {
        "id": PointOfInterestId.SORROW_LOWLAND.value,
        "name": "Низина Скорби",
        "category": PointOfInterestCategory.INFESTATION,
        "is_landmark": True,
        "lore_description": (
            "Место первого контакта Империи с ордой Багрового мицелия. Земля и заброшенные "
            "шахты покрыты пульсирующей багровой грибницей, проросшей сквозь тела крестьян. "
            "Отсюда берут «красные мухоморы» и биомассу."
        ),
        "yield_multipliers": {
            ResourceType.FOOD: 2.2,
        },
        "race_yield_multipliers": {
            FactionRace.GREENSKINS: 1.5,  # Для орков грибница - родная кухня
            FactionRace.CONGREGATION_OF_THE_METEORITE: 1.2,
        },
        "morale_penalty_races": [FactionRace.HUMANS, FactionRace.BARONIAL_TROOPS],
    },
    PointOfInterestId.SIEGE_COLOSSI_GRAVEYARD.value: {
        "id": PointOfInterestId.SIEGE_COLOSSI_GRAVEYARD.value,
        "name": "Кладбище осадных колоссов",
        "category": PointOfInterestCategory.BONEYARD,
        "is_landmark": True,
        "lore_description": (
            "Долина, заваленная остовами гигантских паровых таранов, разбитыми лафетами "
            "мортир и вскрытыми бронекаретами - памятник артиллерийскому тупику первых войн "
            "баронов. Уникальный источник тяжелых бронелистов и орудийных стволов."
        ),
        "yield_multipliers": {
            ResourceType.MATERIAL: 2.8,
            ResourceType.GOLD: 1.3,
        },
        "race_yield_multipliers": {
            FactionRace.BARONIAL_TROOPS: 1.3,  # Их же машины, им и разбирать
        },
        "morale_penalty_races": [],
    },
    # ==================================================================
    # ПРОЦЕДУРНЫЕ МЕСТА
    # ==================================================================
    PointOfInterestId.ASH_GEYSERS.value: {
        "id": PointOfInterestId.ASH_GEYSERS.value,
        "name": "Пепельные гейзеры",
        "category": PointOfInterestCategory.GEO_ANOMALY,
        "is_landmark": False,
        "lore_description": (
            "Поле дышащих трещин, выбрасывающих столбы горячего пепла и серы. Под коркой "
            "остывшего шлака находят спекшиеся самородки и стекловидную породу."
        ),
        "yield_multipliers": {
            ResourceType.MATERIAL: 1.4,
            ResourceType.GOLD: 1.2,
        },
        "race_yield_multipliers": {},
        "morale_penalty_races": [],
    },
    PointOfInterestId.GLASS_GROVES.value: {
        "id": PointOfInterestId.GLASS_GROVES.value,
        "name": "Стеклянные рощи",
        "category": PointOfInterestCategory.GEO_ANOMALY,
        "is_landmark": False,
        "lore_description": (
            "Лес, застигнутый ударной волной осколка и застывший зеленым резонитовым стеклом. "
            "Ветви звенят на ветру и режут руки тем, кто не знает, как их обламывать."
        ),
        "yield_multipliers": {
            ResourceType.MATERIAL: 1.6,
        },
        "race_yield_multipliers": {
            FactionRace.ELFS: 1.4,
            FactionRace.HUMANS: 0.0,  # Резонит людям бесполезен
            FactionRace.BARONIAL_TROOPS: 0.0,
            FactionRace.MERCENARIES: 0.0,
        },
        "morale_penalty_races": [],
    },
    PointOfInterestId.BEAST_BARROWS.value: {
        "id": PointOfInterestId.BEAST_BARROWS.value,
        "name": "Звериные могильники",
        "category": PointOfInterestCategory.BONEYARD,
        "is_landmark": False,
        "lore_description": (
            "Овраги, куда мутировавшие твари стаскивают объедки и умирать приходят сами. "
            "Кости, шкуры и вяленое мясо здесь берут прямо с поверхности."
        ),
        "yield_multipliers": {
            ResourceType.FOOD: 1.5,
            ResourceType.MATERIAL: 1.2,
        },
        "race_yield_multipliers": {
            FactionRace.CONGREGATION_OF_THE_METEORITE: 1.4,
            FactionRace.GREENSKINS: 1.2,
        },
        "morale_penalty_races": [],
    },
    PointOfInterestId.MANUFACTORY_RUINS.value: {
        "id": PointOfInterestId.MANUFACTORY_RUINS.value,
        "name": "Руины мануфактур",
        "category": PointOfInterestCategory.RUINS,
        "is_landmark": False,
        "lore_description": (
            "Выгоревший заводской квартал с обрушенными трубами и застывшими в цехах "
            "станками. Из-под завалов достают инструмент, медь и уцелевшие заготовки."
        ),
        "yield_multipliers": {
            ResourceType.MATERIAL: 1.7,
            ResourceType.GOLD: 1.3,
        },
        "race_yield_multipliers": {
            FactionRace.HUMANS: 1.2,
            FactionRace.BARONIAL_TROOPS: 1.2,
        },
        "morale_penalty_races": [],
    },
}
