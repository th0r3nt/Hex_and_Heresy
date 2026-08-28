"""
Константы фракций: типы ресурсов, категории и уровни зданий, дипломатия.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Final

# ==================================================================
# РЕСУРСЫ
# ==================================================================


class ResourceType(str, Enum):
    """
    Три базовых ресурса, общих для всех фракций.
    """

    GOLD = "gold"
    MATERIAL = "material"
    FOOD = "food"


# ==================================================================
# ЗДАНИЯ - категории
# ==================================================================


class BuildingCategory(str, Enum):
    """
    Функциональная категория здания.
    (см. game_mechanics/building.md)
    """

    ECONOMIC = "economic"
    MILITARY = "military"
    DEFENSIVE = "defensive"
    UNIQUE = "unique"


# ==================================================================
# ГЛАВНОЕ ЗДАНИЕ ФРАКЦИИ
# ==================================================================

MIN_HQ_LEVEL: Final[int] = 0
MAX_HQ_LEVEL: Final[int] = 6

HQ_BASE_BUILDING_SLOTS: Final[int] = 4
HQ_BUILDING_SLOTS_PER_LEVEL: Final[int] = 1


# ==================================================================
# РАТУША/АНАЛОГИ В СОЮЗНЫХ ЗЕМЛЯХ
# ==================================================================

MIN_TOWNHALL_LEVEL: Final[int] = 0
MAX_TOWNHALL_LEVEL: Final[int] = 3
TOWNHALL_BASE_BUILDING_SLOTS: Final[int] = 1
TOWNHALL_BUILDING_SLOTS_PER_LEVEL: Final[int] = 1
TOWNHALL_MAX_BUILDING_SLOTS: Final[int] = 3


# ==================================================================
# ПОГРАНИЧНЫЕ ГОРОДА
# ==================================================================

# Уровни города: 1-й дает 2 строительных слота, каждый следующий - еще один,
# поэтому на потолке (4-м) внутри города помещается 5 построек
MIN_BORDER_TOWN_LEVEL: Final[int] = 1
MAX_BORDER_TOWN_LEVEL: Final[int] = 4

BORDER_TOWN_BASE_BUILDING_SLOTS: Final[int] = 2
BORDER_TOWN_BUILDING_SLOTS_PER_LEVEL: Final[int] = 1

# Сколько смежных гексов город может выкупить себе в союзные земли.
# Столице ее лепестки открыты изначально, город же заселяет их за деньги.
MAX_BORDER_TOWN_ALLIED_LANDS: Final[int] = 4

# Основание города - самая дорогая единовременная трата на карте после
# апгрейда цитадели: обоз с людьми, лесом и провизией на первую зимовку
BORDER_TOWN_FOUNDATION_COST: Final[dict[ResourceType, float]] = {
    ResourceType.GOLD: 400.0,
    ResourceType.MATERIAL: 300.0,
    ResourceType.FOOD: 150.0,
}

# Цена подъема города на очередной уровень. Ключ - целевой уровень,
# то есть тот, на который город встанет после оплаты
BORDER_TOWN_UPGRADE_COST_BY_LEVEL: Final[dict[int, dict[ResourceType, float]]] = {
    2: {ResourceType.GOLD: 300.0, ResourceType.MATERIAL: 250.0},
    3: {ResourceType.GOLD: 500.0, ResourceType.MATERIAL: 400.0},
    4: {ResourceType.GOLD: 800.0, ResourceType.MATERIAL: 650.0},
}

# Выкуп одного смежного гекса под союзную землю города
BORDER_TOWN_LAND_CLAIM_COST: Final[dict[ResourceType, float]] = {
    ResourceType.GOLD: 200.0,
    ResourceType.MATERIAL: 120.0,
}


def border_town_upgrade_cost(target_level: int) -> dict[ResourceType, float]:
    """
    Во что обойдется подъем города до уровня target_level.

    Уровень вне таблицы стоит "ничего": проверять потолок - дело самого
    агрегата BorderTown, а не прайс-листа.
    """
    return dict(BORDER_TOWN_UPGRADE_COST_BY_LEVEL.get(target_level, {}))


# ==================================================================
# СТРОИТЕЛЬСТВО/СНОС
# ==================================================================

BUILDING_DEMOLISH_MATERIAL_REFUND_RATIO: Final[float] = 0.7

MIN_BUILDING_UNLOCK_TIER: Final[int] = 0
MAX_BUILDING_UNLOCK_TIER: Final[int] = 6


# ==================================================================
# РАБОЧИЕ: РИСК/ДОХОДНОСТЬ (см. economy.md)
# ==================================================================


class WorkerRiskTier(str, Enum):
    """Куда отправлен рабочий за ресурсами - определяет риск и доходность."""

    SAFE = "safe"  # шахты на базе
    MODERATE = "moderate"  # заготовка в союзных землях
    HIGH = "high"  # экспедиция в нейтральные земли


WORKER_GOLD_YIELD_SAFE: Final[float] = 10.0
WORKER_GOLD_YIELD_MODERATE: Final[float] = 20.0
WORKER_GOLD_YIELD_HIGH: Final[float] = 50.0

WORKER_GOLD_RATE_BY_TIER: dict[WorkerRiskTier, float] = {
    WorkerRiskTier.SAFE: WORKER_GOLD_YIELD_SAFE,
    WorkerRiskTier.MODERATE: WORKER_GOLD_YIELD_MODERATE,
    WorkerRiskTier.HIGH: WORKER_GOLD_YIELD_HIGH,
}


class WorkerAssignmentType(str, Enum):
    """Тип назначения отряда рабочих."""

    STATIONARY = "stationary"  # Работа в здании (база или союзные земли)
    EXPEDITION = "expedition"  # Экспедиция на нейтральный гекс


class WorkerAssignmentStatus(str, Enum):
    """Статус жизненного цикла назначения рабочих."""

    # Стационарные статусы
    WARMING_UP = "warming_up"  # Переход между зонами (задержка 1 такт)
    WORKING = "working"  # Активная добыча в здании

    # Статусы экспедиции
    TRAVELING_OUT = "traveling_out"  # Марш к нейтральному гексу
    MINING = "mining"  # Добыча на нейтральном гексе (N тактов)
    TRAVELING_BACK = "traveling_back"  # Возвращение с ресурсами на базу

    # Финальные статусы
    COMPLETED = "completed"  # Экспедиция вернулась, груз сдан в казну
    ABORTED = "aborted"  # Прервано из-за гибели отряда или сноса здания


# Базовые значения для рабочих и экспедиций
STATIONARY_WARMUP_TICKS: Final[int] = 1
NEUTRAL_HEX_GOLD_BASE_YIELD_PER_UNIT: Final[float] = (
    2.25  # 225 золота за такт добычи на отряд
)

# ==================================================================
# НАЛОГИ
# ==================================================================

# Границы ставки: 0.0 - налоговые каникулы, 1.0 - базовая норма, 2.0 - грабеж
MIN_TAX_RATE: Final[float] = 0.0
MAX_TAX_RATE: Final[float] = 2.0
BASE_TAX_RATE: Final[float] = 1.0

# Подушный сбор за один уровень административного центра при ставке 1.0
BASE_TAX_HQ_PER_LEVEL: Final[float] = 30.0
BASE_TAX_ZONE_PER_LEVEL: Final[float] = 15.0
BASE_TAX_BORDER_TOWN_PER_LEVEL: Final[float] = 22.0


class TaxPolicyBand(str, Enum):
    """Режим налогообложения, в который попадает выставленная ставка."""

    HOLIDAY = "holiday"  # 0.0 - налоговые каникулы
    REDUCED = "reduced"  # 0.1-0.9 - льготный сбор
    BASELINE = "baseline"  # 1.0 - базовая норма
    RAISED = "raised"  # 1.1-1.4 - повышенные сборы
    PREDATORY = "predatory"  # 1.5-2.0 - грабительские налоги


@dataclass(frozen=True)
class TaxBandEffects:
    """
    Последствия одного режима налогообложения.

    Внутри режима эффекты меняются линейно между границами ставки: чем
    ближе ставка к верхней границе, тем злее подданные.
    """

    band: TaxPolicyBand
    min_rate: float
    max_rate: float
    morale_at_min_rate: float
    morale_at_max_rate: float
    strike_chance: float = 0.0
    riot_chance_at_min_rate: float = 0.0
    riot_chance_at_max_rate: float = 0.0

    def morale_delta(self, rate: float) -> float:
        """Изменение морали гарнизонов при данной ставке (со знаком)."""
        return self._interpolate(rate, self.morale_at_min_rate, self.morale_at_max_rate)

    def riot_chance(self, rate: float) -> float:
        """Вероятность бунта в союзных землях при данной ставке."""
        return self._interpolate(
            rate, self.riot_chance_at_min_rate, self.riot_chance_at_max_rate
        )

    def _interpolate(self, rate: float, at_min: float, at_max: float) -> float:
        """Линейная интерполяция значения между границами режима."""
        if self.max_rate <= self.min_rate:
            return at_min
        position = (rate - self.min_rate) / (self.max_rate - self.min_rate)
        position = min(1.0, max(0.0, position))
        return at_min + (at_max - at_min) * position


# Таблица режимов по возрастанию ставки (см. _TODO.md, механика налогов)
TAX_BANDS: Final[tuple[TaxBandEffects, ...]] = (
    TaxBandEffects(
        band=TaxPolicyBand.HOLIDAY,
        min_rate=0.0,
        max_rate=0.0,
        morale_at_min_rate=5.0,
        morale_at_max_rate=5.0,
    ),
    TaxBandEffects(
        band=TaxPolicyBand.REDUCED,
        min_rate=0.1,
        max_rate=0.9,
        morale_at_min_rate=4.0,
        morale_at_max_rate=2.0,
    ),
    TaxBandEffects(
        band=TaxPolicyBand.BASELINE,
        min_rate=1.0,
        max_rate=1.0,
        morale_at_min_rate=0.0,
        morale_at_max_rate=0.0,
    ),
    TaxBandEffects(
        band=TaxPolicyBand.RAISED,
        min_rate=1.1,
        max_rate=1.4,
        morale_at_min_rate=-3.0,
        morale_at_max_rate=-8.0,
        strike_chance=0.05,
    ),
    TaxBandEffects(
        band=TaxPolicyBand.PREDATORY,
        min_rate=1.5,
        max_rate=2.0,
        morale_at_min_rate=-10.0,
        morale_at_max_rate=-20.0,
        riot_chance_at_min_rate=0.10,
        riot_chance_at_max_rate=0.20,
    ),
)


def resolve_tax_band(rate: float) -> TaxBandEffects:
    """
    Подбирает режим налогообложения для произвольной ставки ползунка.

    Ставку между режимами (например, 0.95) забирает следующий по строгости
    режим: сомнения трактуются не в пользу казны.
    """
    for effects in TAX_BANDS:
        if rate <= effects.max_rate:
            return effects
    return TAX_BANDS[-1]


# ==================================================================
# ДИПЛОМАТИЯ
# ==================================================================


class DiplomaticStance(str, Enum):
    """Базовое состояние отношений между двумя фракциями."""

    PEACE = "peace"
    WAR = "war"


class AmbassadorStatus(str, Enum):
    """Текущий статус посла на глобальной карте."""

    TRAVELING = "traveling"
    IN_AUDIENCE = "in_audience"
    EXECUTED = "executed"
    RETURNED = "returned"


class NegotiationMode(str, Enum):
    """Режим ведения переговоров послом."""

    MANUAL = "manual"
    AUTOMATIC = "automatic"


class DiplomaticActionType(str, Enum):
    """Функции, которые лорд может вызвать по итогам переговоров."""

    NONE = "none"  # Лорд ограничился словами
    DECLARE_WAR = "declare_war"
    MAKE_PEACE = "make_peace"
    PROPOSE_TRADE = "propose_trade"
    ESTABLISH_BORDERS = "establish_borders"
    ESTABLISH_RIGHT_OF_PASSAGE = "establish_right_of_passage"
    DEMAND_TRIBUTE = "demand_tribute"
    EXECUTE_AMBASSADOR = "execute_ambassador"


# Гонец с депешей: скорость движения и риск перехвата (см. game_mechanics/diplomacy.md)
DISPATCH_COURIER_SPEED_HEXES: Final[int] = 4
DISPATCH_INTERCEPT_CHANCE: Final[float] = 0.20

# Оплата труда гонца: фиксированная часть плюс надбавка за каждый гекс пути
DISPATCH_BASE_COST_GOLD: Final[float] = 10.0
DISPATCH_COST_GOLD_PER_HEX: Final[float] = 2.5

# Скорость пешего посла без охраны (с охраной он идет со скоростью её армии)
AMBASSADOR_SPEED_HEXES: Final[int] = 2

# Предел реплик в автоматических переговорах двух LLM, чтобы диалог не зациклился
MAX_AUTO_NEGOTIATION_ROUNDS: Final[int] = 6


# ==================================================================
# ГАРНИЗОНЫ ЗЕМЕЛЬ (см. _TODO.md, механика гарнизона)
# ==================================================================

# Сколько карточек регулярных войск игрок может расквартировать на одной земле
MAX_STATIONED_GARRISON_SQUADS: Final[int] = 10

# Насколько меньше провизии ест отряд за стенами: 0.55 - это минус 55%
GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO: Final[float] = 0.55

# Из отрядов каких тиров набирается городское ополчение
MILITIA_ALLOWED_TIERS: Final[tuple[int, ...]] = (1, 2)

# Вместимость ополчения по уровню цитадели/ратуши. Уровень 0 - стройка
# еще не поднялась, защищать землю некому.
MILITIA_CAPACITY_BY_LEVEL: Final[dict[int, int]] = {
    0: 0,
    1: 2,
    2: 3,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
}

# Доля полного состава, которую ополчение добирает из горожан за один такт
MILITIA_REPLENISHMENT_RATE_PER_TICK: Final[float] = 0.15


def militia_capacity_for_level(level: int) -> int:
    """
    Сколько отрядов ополчения держит здание такого уровня.

    Уровень выше таблицы (последствие будущих модификаторов) не должен
    ронять расчет такта - берется вместимость максимального известного уровня.
    """
    if level in MILITIA_CAPACITY_BY_LEVEL:
        return MILITIA_CAPACITY_BY_LEVEL[level]
    if level < 0:
        return 0
    return MILITIA_CAPACITY_BY_LEVEL[max(MILITIA_CAPACITY_BY_LEVEL)]
