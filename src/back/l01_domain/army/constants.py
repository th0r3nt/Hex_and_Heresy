"""
Константы армии, лимиты отрядов и базовые механические коэффициенты.
"""

from enum import Enum
from typing import Final

# Лимиты отряда
MAX_SQUAD_UNITS: Final[int] = 500
MIN_SQUAD_UNITS: Final[int] = 1

# Лимиты параметров
MAX_MORALE: Final[float] = 100.0
MIN_MORALE: Final[float] = 0.0
PANIC_THRESHOLD_MORALE: Final[float] = 20.0

MAX_STAMINA: Final[float] = 100.0
MIN_STAMINA: Final[float] = 0.0
EXHAUSTION_THRESHOLD_STAMINA: Final[float] = 15.0

# Лимиты героя
MAX_HERO_LEVEL: Final[int] = 20


class DamageType(str, Enum):
    """Тип наносимого урона."""

    SLASHING = "slashing"  # Рубящий
    PIERCING = "piercing"  # Колющий
    BLUDGEONING = "bludgeoning"  # Дробящий
    MAGIC = "magic"  # Магический
    FIRE = "fire"  # Огненный
    ICE = "ice"  # Ледяной


class EquipmentSlot(str, Enum):
    """Слот, который занимает предмет экипировки."""

    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"


class UnitSizeCategory(str, Enum):
    """
    Габарит юнита. Влияет на бонус урона оружия против цели такого размера.
    """

    SMALL = "small"  # гоблины, крысы
    MEDIUM = "medium"  # люди, орки, эльфы
    LARGE = "large"  # кавалерия, крупные звери
    HUGE = "huge"  # огры, драконы, монстры

class StrategicMovementPace(str, Enum):
    """
    Темп марша армии на глобальной карте (в гексах за один такт).
    (см. strategic_map.md)
    """

    CAUTIOUS = "cautious"  # Осторожный шаг (1 гекс/7.5 км за 1 такт (4 часа игрового времени))
    MARCH = "march"  # Обычный марш (2 гекса / 15 км)
    FORCED = "forced"  # Форсированный марш (3 гекса / 22.5 км)
    MOUNTED = "mounted"  # Конный марш (4 гекса / 30 км)


STRATEGIC_PACE_SPEED_HEXES: Final[dict[StrategicMovementPace, int]] = {
    StrategicMovementPace.CAUTIOUS: 1,
    StrategicMovementPace.MARCH: 2,
    StrategicMovementPace.FORCED: 3,
    StrategicMovementPace.MOUNTED: 4,
}