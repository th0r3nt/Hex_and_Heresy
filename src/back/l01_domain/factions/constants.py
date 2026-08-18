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
    (см. economy.md)
    """

    GOLD = "gold"
    MATERIAL = "material"
    FOOD = "food"


# ==================================================================
# ЗДАНИЯ — категории и зоны застройки
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


class TerritoryZoneType(str, Enum):
    """
    Тип зоны, где вообще разрешена застройка.
    """

    BASE = "base"
    ALLIED_LANDS = "allied_lands"
    NEUTRAL_LANDS = "neutral_lands"


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
    """Куда отправлен рабочий за ресурсами — определяет риск и доходность."""

    SAFE = "safe"  # шахты на базе
    MODERATE = "moderate"  # заготовка в союзных землях
    HIGH = "high"  # экспедиция в нейтральные земли


# Числа - иллюстративный пример из economy.md, не финальный баланс
WORKER_GOLD_YIELD_SAFE: Final[float] = 10.0
WORKER_GOLD_YIELD_MODERATE: Final[float] = 20.0
WORKER_GOLD_YIELD_HIGH: Final[float] = 50.0


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
