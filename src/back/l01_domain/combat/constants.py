"""
Константы тактического боя: геометрия сетки, дальности атак, темп передвижения.

Простые Enum, не несущие собственных данных.
"""

from enum import Enum
from typing import Final

# ==================================================================
# ГЕОМЕТРИЯ И ВРЕМЯ
# ==================================================================

CELL_SIZE_METERS: Final[float] = 25.0 # 25 * 25
TURN_DURATION_SECONDS: Final[int] = 30


class BattleMapSize(str, Enum):
    """Формат тактической карты."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


# черновые значения, требуют утверждения гейм-дизайном
BATTLE_MAP_DIMENSIONS: Final[dict[BattleMapSize, tuple[int, int]]] = {
    BattleMapSize.SMALL: (11, 11),
    BattleMapSize.MEDIUM: (13, 13),
    BattleMapSize.LARGE: (15, 15),
}

# Зона развертки войск перед началом боя
DEPLOYMENT_ZONE_DEPTH_CELLS: Final[int] = 10 # TODO: должно занимать полную ширину карты, несмотря на размер, и иметь длину, зависящую от размера 

NIGHT_VISION_RANGE_CELLS: Final[int] = 3


# ==================================================================
# ДАЛЬНОСТЬ АТАК (в клетках)
# ==================================================================

MELEE_SHORT_RANGE_CELLS: Final[int] = 1
MELEE_LONG_RANGE_CELLS: Final[int] = 2
FIREARM_RANGE_CELLS_MIN: Final[int] = 4
FIREARM_RANGE_CELLS_MAX: Final[int] = 5
BOW_RANGE_CELLS_MIN: Final[int] = 6
BOW_RANGE_CELLS_MAX: Final[int] = 10
SIEGE_RANGE_CELLS_MIN: Final[int] = 15
SIEGE_RANGE_CELLS_MAX: Final[int] = 20


# ==================================================================
# ТЕМП ПЕРЕДВИЖЕНИЯ
# ==================================================================

# Базовые значения скорости передвижения умножаются на следующие значения в зависимости от выбранной скорости
SPEED_DEFENSE_PACE: Final[float] = 0.0 # Оборона на месте
SPEED_TACTICAL_PACE: Final[float] = 0.5 # Тактический шаг, сохраняющий доп. оборону на 0.5
SPEED_SLOW_PACE: Final[float] = 0.75  # Замедленный шаг, сохраняющий доп. оборону на 0.25
SPEED_MARCH_PACE: Final[float] = 1.0
SPEED_CHARGE_PACE: Final[float] = 2.0

CHARGE_DAMAGE_BONUS: Final[float] = 1.5


# ==================================================================
# МОРАЛЬ И ПОСЛЕДСТВИЯ БОЯ
# ==================================================================

CHAIN_PANIC_RADIUS_CELLS: Final[int] = 1 # Если отряд пал духом на поле боя - он деморализирует соседние отряды в радиусе 1 клетки
CORPSE_PILE_UNIT_THRESHOLD: Final[int] = 150 # Если на одной клетке падет больше 150 юнитов - клетка превратится в местность "куча трупов"
# TODO: ввести критерий размера юнита, влияющий на бонус дальней атаки и атаки древковым оружием, а также на заполненность кучи трупов на клетке


# ==================================================================
# КЛАССИФИКАЦИИ (простые Enum без собственных данных)
# ==================================================================


class SurfaceIncline(str, Enum):
    """
    Наклон поверхности клетки - влияет на бонус натиска 
    и стоимость выносливости при передвижении.
    """

    FLAT = "flat"
    ASCENT = "ascent"
    DESCENT = "descent"


class TerrainType(str, Enum):
    """
    Тип местности клетки. 
    Расширяется под лор конкретных гексов.
    """

    PLAIN = "plain"
    FOREST = "forest"
    SWAMP = "swamp"
    MOUNTAIN = "mountain"
    RUINS = "ruins"
    CORPSE_PILE = "corpse_pile"


class CombatEffectCategory(str, Enum):
    """
    Источник боевого эффекта - нужен для UI и логов летописца.
    """

    ENVIRONMENTAL = "environmental"
    STATUS = "status"
    WEATHER = "weather"


class EffectStackingRule(str, Enum):
    """
    Что происходит при повторном наложении эффекта.
    """

    REFRESH = "refresh"
    STACK = "stack"
    IGNORE = "ignore"


class BattlePhase(str, Enum):
    """
    Фаза текущего тактического хода.
    """

    DEPLOYMENT = "deployment"
    ORDERS = "orders"
    REACTION = "reaction"
    RESOLUTION = "resolution"
    AFTERMATH = "aftermath"


class ReactionType(str, Enum):
    """
    Реакция защищающегося отряда на натиск.
    (см. fighting.md, "Механика реакций")
    """

    ACCEPT_CHARGE = "accept_charge"
    COUNTER_CHARGE = "counter_charge"
    FLEE = "flee"


class WeatherCondition(str, Enum):
    """
    Погодные условия боя.
    """

    CLEAR = "clear"
    HEAVY_RAIN = "heavy_rain"
    SNOWFALL = "snowfall"
    CLOUDY = "cloudy"
    # TODO: добавить больше и описать механику действия


class TimeOfDay(str, Enum):
    """Время суток по лору мира. 
    (см. lore/timekeeping_system.md)"""

    GREY_HOURS = "grey_hours"
    NEON_HOURS = "neon_hours"
