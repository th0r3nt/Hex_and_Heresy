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
