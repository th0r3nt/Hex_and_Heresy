"""
Константы тактического боя: геометрия сетки, дальности атак, темп передвижения.

Простые Enum, не несущие собственных данных.
"""

from enum import Enum
from typing import Final

from src.back.l01_domain.army.constants import UnitSizeCategory

# ==================================================================
# ГЕОМЕТРИЯ И ВРЕМЯ
# ==================================================================

CELL_SIZE_METERS: Final[float] = 25.0  # 25 * 25
TURN_DURATION_SECONDS: Final[int] = 30


class BattleMapSize(str, Enum):
    """Формат тактической карты."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


# Черновые значения, требуют утверждения гейм-дизайном
BATTLE_MAP_DIMENSIONS: Final[dict[BattleMapSize, tuple[int, int]]] = {
    BattleMapSize.SMALL: (14, 14),
    BattleMapSize.MEDIUM: (17, 17),
    BattleMapSize.LARGE: (20, 20),
}

# Зона развертки войск перед началом боя
# Ширина зоны (перпендикулярно направлению атаки)
# всегда равна полной ширине карты.
# Здесь фиксируется только глубина (в клетках от края карты),
# которая растёт вместе с размером карты
# Черновые значения, требуют утверждения гейм-дизайном
DEPLOYMENT_ZONE_DEPTH_CELLS: Final[dict[BattleMapSize, int]] = {
    BattleMapSize.SMALL: 3,
    BattleMapSize.MEDIUM: 4,
    BattleMapSize.LARGE: 5,
}

# Базовая дальность обзора отряда в клетках.
# Днем при ясной погоде она заведомо перекрывает самую большую карту (20x20),
# то есть поле просматривается целиком; ночь и непогода режут ее вниз.
DAY_VISION_RANGE_CELLS: Final[int] = 20
NIGHT_VISION_RANGE_CELLS: Final[int] = 3
# Совсем ослепнуть нельзя: соседнюю клетку видно даже в токсичном тумане ночью
MIN_VISION_RANGE_CELLS: Final[int] = 1

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
SPEED_DEFENSE_PACE: Final[float] = 0.0  # Оборона на месте
SPEED_TACTICAL_PACE: Final[float] = 0.5  # Тактический шаг, сохраняющий доп. оборону на 0.5
SPEED_SLOW_PACE: Final[float] = 0.75  # Замедленный шаг, сохраняющий доп. оборону на 0.25
SPEED_MARCH_PACE: Final[float] = 1.0
SPEED_CHARGE_PACE: Final[float] = 2.0

CHARGE_DAMAGE_BONUS: Final[float] = 1.5


class TacticalMovementPace(str, Enum):
    """
    Темп движения отряда в тактическом бою.
    """

    DEFENSE = "defense"
    TACTICAL = "tactical"
    SLOW = "slow"
    MARCH = "march"
    CHARGE = "charge"


TACTICAL_PACE_SPEEDS: Final[dict[TacticalMovementPace, float]] = {
    TacticalMovementPace.DEFENSE: SPEED_DEFENSE_PACE,
    TacticalMovementPace.TACTICAL: SPEED_TACTICAL_PACE,
    TacticalMovementPace.SLOW: SPEED_SLOW_PACE,
    TacticalMovementPace.MARCH: SPEED_MARCH_PACE,
    TacticalMovementPace.CHARGE: SPEED_CHARGE_PACE,
}


# ==================================================================
# МОРАЛЬ И ПОСЛЕДСТВИЯ БОЯ
# ==================================================================

CHAIN_PANIC_RADIUS_CELLS: Final[int] = (
    1  # Если отряд пал духом на поле боя - он деморализирует соседние отряды в радиусе 1 клетки
)
CORPSE_PILE_UNIT_THRESHOLD: Final[int] = (
    150  # Если на одной клетке падет больше 150 юнитов - клетка превратится в местность "куча трупов"
)

# Вес одного погибшего бойца для расчёта заполненности кучи трупов
# Например, огр занимает место как несколько десятков людей
# Черновые значения, требуют утверждения гейм-дизайном
UNIT_SIZE_CORPSE_WEIGHT: Final[dict[UnitSizeCategory, float]] = {
    UnitSizeCategory.SMALL: 0.5,
    UnitSizeCategory.MEDIUM: 1.0,
    UnitSizeCategory.LARGE: 5.0,
    UnitSizeCategory.HUGE: 20.0,
}
# ==================================================================
# НАТИСК И РЕАКЦИИ
# ==================================================================

# Черновые значения, требуют утверждения гейм-дизайном
MORALE_THRESHOLD_ACCEPT_CHARGE: Final[float] = (
    35.0  # мин. мораль, чтобы удержать строй и "принять удар"
)
ACCEPT_CHARGE_DEFENDER_DAMAGE_RATIO: Final[float] = (
    0.4  # доля урона натиска, которую защитник всё равно получает при успешном приёме
)
FLEE_CATCH_DAMAGE_MULTIPLIER: Final[float] = 1.7  # урон при поимке бегущего отряда
DOWNHILL_CHARGE_DAMAGE_MULTIPLIER: Final[float] = 1.3  # бонус натиска с холма
UPHILL_CHARGE_DAMAGE_PENALTY: Final[float] = 0.7  # штраф натиска снизу вверх
CHAIN_PANIC_MORALE_SHOCK: Final[float] = (
    10.0  # удар по морали соседей/при несостоявшемся приёме удара
)

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


class FacingAngle(str, Enum):
    """
    Угол атаки в рукопашной схватке относительно направления,
    куда смотрит защищающийся отряд.
    """

    FRONT = "front"
    FLANK = "flank"
    REAR = "rear"


class WeatherCondition(str, Enum):
    """
    Погодные условия боя. Конкретные игровые эффекты каждого условия -
    см. combat/weather.py, get_weather_combat_effects().
    """

    CLEAR = "clear"  # без штрафов
    HEAVY_RAIN = "heavy_rain"  # луки намокают, аркебузы чаще дают осечку
    SNOWFALL = "snowfall"  # снижена скорость и видимость
    CLOUDY = "cloudy"  # незначительное снижение видимости
    ASH_STORM = "ash_storm"  # пепел стратосферы прибивает к земле; видимость как ночью, отряды без масок задыхаются (быстрее теряют выносливость)
    TOXIC_MIST = "toxic_mist"  # испарения Ничьей земли; урон по тактам, снижена видимость
    MAGNETIC_STORM = "magnetic_storm"  # магия отключена на весь бой; люди воодушевлены, эльфы дезориентированы


class TimeOfDay(str, Enum):
    """Время суток по лору мира.
    (см. lore/timekeeping_system.md)"""

    GREY_HOURS = "grey_hours"
    NEON_HOURS = "neon_hours"
