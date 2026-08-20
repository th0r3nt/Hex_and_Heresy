"""
Константы фракций: типы ресурсов, категории и уровни зданий, дипломатия.
"""

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
MAX_TOWNHALL_LEVEL: Final[int] = 2
TOWNHALL_BASE_BUILDING_SLOTS: Final[int] = 1
TOWNHALL_BUILDING_SLOTS_PER_LEVEL: Final[int] = 1
TOWNHALL_MAX_BUILDING_SLOTS: Final[int] = 3


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
    0.5  # 50 золота за полный отряд из 100 рабочих за такт
)

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
