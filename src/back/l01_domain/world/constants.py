"""
Константы глобального мира: временные циклы, параметры суток, классификация
глобальных событий и настройки генератора новой партии.
"""

from enum import Enum
from typing import Final

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.maps.constants import HexDirection

# ==================================================================
# СИСТЕМА ЛЕТОИСЧИСЛЕНИЯ
# ==================================================================

# Сутки длятся 28 часов из-за замедления вращения планеты после Катаклизма
HOURS_PER_DAY: Final[int] = 28
GREY_HOURS_COUNT: Final[int] = 16
NEON_HOURS_COUNT: Final[int] = 12

# Цикл (год) длится 300 суток
DAYS_PER_CYCLE: Final[int] = 300

# Количество часов в одном глобальном такте (ходе) по умолчанию
DEFAULT_HOURS_PER_TICK: Final[int] = 4

# ==================================================================
# МАРОДЕРСТВО И ПОЛЯ БРАНИ
# ==================================================================

# Количество тактов, в течение которых поле брани сохраняет трофеи до полного разложения
DEFAULT_BATTLEFIELD_DECAY_TICKS: Final[int] = 12

# Базовый шанс уцелеть для предмета экипировки в бою (до модификаторов)
DEFAULT_EQUIPMENT_SALVAGE_RATIO: Final[float] = 0.35


# ==================================================================
# КЛАССИФИКАЦИЯ ГЛОБАЛЬНЫХ СОБЫТИЙ
# ==================================================================


class GlobalEventCategory(str, Enum):
    """
    Категория глобального события, генерируемого мастером игры.
    """

    WEATHER = "weather"  # погодные и радиационные аномалии (напр. магнитная буря)
    ECONOMIC = "economic"  # кризисы, неурожаи, бунты на шахтах
    MILITARY = "military"  # рейды нейтральных банд, кровная месть
    LORE_CRISIS = "lore_crisis"  # выбросы первичной взвеси, резонансы


class GlobalEventScope(str, Enum):
    """
    Масштаб распространения события.
    """

    GLOBAL = "global"  # действует на весь мир и все фракции
    FACTION = "faction"  # затрагивает конкретную фракцию
    ZONE = "zone"  # локализовано на конкретных гексах карты


# ==================================================================
# ЛЕТОПИСЕЦ И ЗАЛ ПАВШИХ (см. docs/game_mechanics/chronicler.md)
# ==================================================================

# Бой попадает в летопись, если с каждой стороны стояло не меньше стольких карточек.
# Стычки меньшего масштаба уходят только в фоновые слухи
CHRONICLE_MIN_SQUADS_PER_SIDE: Final[int] = 6

# Доля погибших от исходной численности стороны, после которой бой считается резней
CHRONICLE_MASSACRE_LOSS_RATIO: Final[float] = 0.6

# Сколько отрядов должны запаниковать в одном раунде, чтобы это считалось цепной паникой
CHRONICLE_CHAIN_PANIC_SQUADS: Final[int] = 2

# Сколько тактов без единого боя терпит летописец, прежде чем начать разносить слухи
RUMOR_IDLE_TICKS_THRESHOLD: Final[int] = 3

# Размер страницы витрины летописи и Зала павших для интерфейса
CHRONICLE_HISTORY_PAGE_SIZE: Final[int] = 50

# Лимиты длины текстов от языковой модели: свиток должен помещаться в окно интерфейса
CHRONICLE_TITLE_MAX_LENGTH: Final[int] = 120
CHRONICLE_QUOTE_MAX_LENGTH: Final[int] = 400
CHRONICLE_BODY_MAX_LENGTH: Final[int] = 4000
RUMOR_TEXT_MAX_LENGTH: Final[int] = 300


# ==================================================================
# ГЛОБАЛЬНЫЕ ЦЕЛИ ПАРТИИ (см. docs/game_mechanics/victory.md)
# ==================================================================


class VictoryType(str, Enum):
    """
    Три способа выиграть партию.
    """

    # Территориальное господство: у соперников не осталось действующих цитаделей
    DOMINATION = "domination"
    # Экономическое процветание: казна одновременно держит все три порога
    ECONOMIC = "economic"
    # Основание страны: три пограничных города доведены до четвертого уровня
    EXPANSION = "expansion"


# Пороги экономической победы. Считаются одновременно: перевес золота не
# заменяет пустых амбаров, поэтому казна обязана взять все три планки разом
VICTORY_ECONOMIC_GOLD: Final[float] = 6000.0
VICTORY_ECONOMIC_MATERIAL: Final[float] = 4000.0
VICTORY_ECONOMIC_FOOD: Final[float] = 8000.0

# Пороги градостроительной победы: сколько городов и какого уровня нужно
# держать ОДНОВРЕМЕННО. Разграбленный город выпадает из зачета, пока не
# отстроится обратно
VICTORY_EXPANSION_TOWNS_COUNT: Final[int] = 3
VICTORY_EXPANSION_TOWN_LEVEL: Final[int] = 4


# ==================================================================
# ГЕНЕРАТОР НОВОЙ ПАРТИИ: УРОВНИ СЛОЖНОСТИ
# ==================================================================


class DifficultyLevel(str, Enum):
    """
    Уровень сложности партии.

    Сложность не трогает боевую математику: она задает только стартовые
    пулы ресурсов. На легком фору получает игрок, на тяжелом - его
    соперники, на нормальном обе стороны начинают с одинаковой казны.
    """

    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


# Стартовая казна игрока по уровням сложности
STARTING_RESOURCES_PLAYER: Final[dict[DifficultyLevel, dict[ResourceType, float]]] = {
    DifficultyLevel.EASY: {
        ResourceType.GOLD: 1500.0,
        ResourceType.MATERIAL: 500.0,
        ResourceType.FOOD: 600.0,
    },
    DifficultyLevel.NORMAL: {
        ResourceType.GOLD: 1000.0,
        ResourceType.MATERIAL: 300.0,
        ResourceType.FOOD: 400.0,
    },
    DifficultyLevel.HARD: {
        ResourceType.GOLD: 600.0,
        ResourceType.MATERIAL: 200.0,
        ResourceType.FOOD: 250.0,
    },
}

# Стартовая казна соперника-ИИ и баронств: зеркало таблицы игрока.
# На легком фору получает игрок, на тяжелом - его противники
STARTING_RESOURCES_RIVAL: Final[dict[DifficultyLevel, dict[ResourceType, float]]] = {
    DifficultyLevel.EASY: {
        ResourceType.GOLD: 800.0,
        ResourceType.MATERIAL: 300.0,
        ResourceType.FOOD: 300.0,
    },
    DifficultyLevel.NORMAL: {
        ResourceType.GOLD: 1000.0,
        ResourceType.MATERIAL: 300.0,
        ResourceType.FOOD: 400.0,
    },
    DifficultyLevel.HARD: {
        ResourceType.GOLD: 1500.0,
        ResourceType.MATERIAL: 500.0,
        ResourceType.FOOD: 600.0,
    },
}


def starting_resources(
    difficulty: DifficultyLevel, is_player_controlled: bool
) -> dict[ResourceType, float]:
    """
    Стартовая казна стороны на выбранной сложности.

    Возвращается копия: партия сразу начинает тратить эти деньги, а таблица
    констант должна пережить всю сессию нетронутой.
    """
    table = STARTING_RESOURCES_PLAYER if is_player_controlled else STARTING_RESOURCES_RIVAL
    return dict(table[difficulty])


# ==================================================================
# ГЕНЕРАТОР НОВОЙ ПАРТИИ: РАЗМЕТКА КАРТЫ
# ==================================================================

# Лепестки, которые сторона занимает на нулевом такте. Всего вокруг цитадели
# шесть смежных гексов, но обжитыми партия начинается с трех: остальные игрок
# и ИИ забирают уже по ходу игры.
#
# Ровно три, а не два, потому что ратуша первого уровня дает один строительный
# слот, а стартовая застройка - это три здания (см. STARTING_BUILDING_PLAN)
STARTING_ALLIED_LANDS_COUNT: Final[int] = 3

# Куда смотрят эти лепестки. Обе стороны занимают западную дугу вокруг своей
# цитадели, поэтому свободный фланг у них обращен в центр - к сопернику.
# Порядок важен: по нему раскладывается стартовая застройка
NORTH_BASE_ALLIED_DIRECTIONS: Final[tuple[HexDirection, ...]] = (
    HexDirection.WEST,
    HexDirection.SOUTHWEST,
    HexDirection.NORTHWEST,
)
SOUTH_BASE_ALLIED_DIRECTIONS: Final[tuple[HexDirection, ...]] = (
    HexDirection.WEST,
    HexDirection.NORTHWEST,
    HexDirection.SOUTHWEST,
)
BARONY_ALLIED_DIRECTIONS: Final[tuple[HexDirection, ...]] = (
    HexDirection.WEST,
    HexDirection.SOUTHWEST,
    HexDirection.NORTHWEST,
)

# Замок независимых баронств встает где-то в центре Ничьей земли: ряд экватора
# и небольшой разброс по горизонтали, чтобы обеим сторонам он мешал одинаково
BARONY_CENTER_ROW_R: Final[int] = 0
BARONY_CENTER_Q_RANGE: Final[tuple[int, int]] = (-2, 2)

# Пояс, в котором расставляются лорные ориентиры Ничьей земли: |r| <= 2.
# Именно там проходят главные торговые и военные маршруты между цитаделями
NO_MANS_LAND_LANDMARK_BELT_RADIUS: Final[int] = 2

# Плотность процедурных мест на оставшихся нейтральных гексах. Конкретное
# значение из этого диапазона выбирает сид партии, поэтому один мир выходит
# богаче другого, но оба воспроизводимы
PROCEDURAL_POI_DENSITY_RANGE: Final[tuple[float, float]] = (0.04, 0.08)

# Остаточный резонит в застарелых полях брани лорных ориентиров. Такие поля
# нетленны: они стоят веками и таймеру гниения не подчиняются
LANDMARK_BATTLEFIELD_RESONITE_RANGE: Final[tuple[float, float]] = (40.0, 120.0)


# ==================================================================
# ГЕНЕРАТОР НОВОЙ ПАРТИИ: РАСОВЫЕ НАЗВАНИЯ ЦЕНТРОВ УПРАВЛЕНИЯ
# ==================================================================

# Как называется главное здание фракции у каждой расы (см. docs/factions/*)
HEADQUARTERS_NAME_BY_RACE: Final[dict[FactionRace, str]] = {
    FactionRace.HUMANS: "Цитадель",
    FactionRace.GREENSKINS: "Шатер Вождя",
    FactionRace.ELFS: "Парящее святилище",
    FactionRace.BARONIAL_TROOPS: "Замок Барона",
    FactionRace.CONGREGATION_OF_THE_METEORITE: "Алтарь Прародителя",
}

# Как называется административный центр союзной земли у каждой расы
REGIONAL_HALL_NAME_BY_RACE: Final[dict[FactionRace, str]] = {
    FactionRace.HUMANS: "Ратуша",
    FactionRace.GREENSKINS: "Сборный пункт",
    FactionRace.ELFS: "Малое святилище",
    FactionRace.BARONIAL_TROOPS: "Ратуша",
    FactionRace.CONGREGATION_OF_THE_METEORITE: "Тайное святилище",
}

# Запасные названия на случай расы без своей записи в таблицах выше
DEFAULT_HEADQUARTERS_NAME: Final[str] = "Цитадель"
DEFAULT_REGIONAL_HALL_NAME: Final[str] = "Ратуша"


# ==================================================================
# ГЕНЕРАТОР НОВОЙ ПАРТИИ: СТАРТОВАЯ АРМИЯ
# ==================================================================

# Из кого состоит армия нулевого такта. Полководца у нее нет: пока игрок
# или ИИ не назначит лидера, армия стоит на гексе цитадели
STARTING_ARMY_WORKER_SQUADS: Final[int] = 2
STARTING_ARMY_INFANTRY_SQUADS: Final[int] = 2

# Тир рабочих и тир регулярной пехоты в расовом ростере
WORKER_UNIT_TIER: Final[int] = 0
STARTING_INFANTRY_UNIT_TIER: Final[int] = 1

STARTING_ARMY_NAME: Final[str] = "Ополчение державы"
