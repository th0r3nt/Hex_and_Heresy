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


class WeaponCategory(str, Enum):
    """Категория и тип оружия."""

    # Ближний бой
    SWORD = "sword"
    AXE = "axe"
    POLEARM = "polearm"
    SPEAR = "spear"
    DAGGER = "dagger"
    WHIP = "whip"
    GREATSWORD = "greatsword"

    # Дальний бой
    BOW = "bow"
    CROSSBOW = "crossbow"
    FIREARM = "firearm"
    THROWING = "throwing"
    SIEGE_ENGINE = "siege_engine"

    # Особое
    MAGIC = "magic"
    NATURAL = "natural" # Клыки, когти и т.п.


class ArmorCategory(str, Enum):
    """Категория и материал брони."""

    UNARMORED = "unarmored"
    CLOTH = "cloth"
    PADDED = "padded"
    LEATHER = "leather"
    MAIL = "mail"
    BRIGANDINE = "brigandine"
    PLATE = "plate"
    CARAPACE = "carapace"
    FORCE_FIELD = "force_field" # Для магов


class AccessoryCategory(str, Enum):
    """Категория аксессуара."""

    SHIELD = "shield"
    BANNER = "banner"
    AMMUNITION = "ammunition"
    TRAP = "trap"
    RELIC = "relic"
    POTION = "potion"
    INSTRUMENT = "instrument"
    MISC = "misc"


class EquipmentTag(str, Enum):
    """Механические и лорные свойства предметов экипировки."""

    # Погодные и физические свойства
    BLACKPOWDER = "blackpowder"  # Черный порох (осечки при ливне)
    STRING_BASED = "string_based"  # Тетива (намокает при ливне)
    FLAMMABLE = "flammable"  # Легковоспламеняющийся предмет
    HEAVY = "heavy"  # Повышенный расход выносливости

    # Боевые свойства и хват
    ONE_HANDED = "one_handed"
    TWO_HANDED = "two_handed"
    BRACEABLE = "braceable"  # Упор против натиска
    SHIELD_BREAKER = "shield_breaker"  # Эффективно против щитов
    ARMOR_PIERCING = "armor_piercing"

    # Лорные и магические свойства
    SILVER = "silver"  # Эффективно против нежити и мутантов
    RESONITE_POWERED = "resonite_powered"  # Резонитовая природа
    CURSED = "cursed"  # Проклятый предмет


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
