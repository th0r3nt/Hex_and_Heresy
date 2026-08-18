"""
Константы и перечисления геометрии карт: направления, зонирование, масштаб и параметры 271-гексагонной сетки.
"""

from enum import Enum
from typing import Final

# ==================================================================
# ЗОНИРОВАНИЕ ТЕРРИТОРИЙ И МАСШТАБ
# ==================================================================


class TerritoryZoneType(str, Enum):
    """
    Тип зоны гексагональной карты.
    """

    BASE = "base"
    ALLIED_LANDS = "allied_lands"
    NEUTRAL_LANDS = "neutral_lands"


# Физический масштаб: расстояние между центрами соседних гексов
HEX_SCALE_KM: Final[float] = 7.5

# Радиус лепестков союзных земель вокруг цитадели
ALLIED_LANDS_RING_RADIUS: Final[int] = 1

# ==================================================================
# ПАРАМЕТРЫ СТАНДАРТНОЙ КАРТЫ (271 гекс, 19 рядов)
# ==================================================================

GLOBAL_MAP_TOTAL_ROWS: Final[int] = 19
GLOBAL_MAP_ROW_LENGTHS: Final[tuple[int, ...]] = (
    10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10
)
GLOBAL_MAP_TOTAL_HEXES: Final[int] = 271

# Дистанция в гексах между Северной и Южной цитаделями
DISTANCE_BETWEEN_CITADELS_HEXES: Final[int] = 16


# ==================================================================
# НАПРАВЛЕНИЯ ГЕКСАГОНАЛЬНОЙ СЕТКИ (кубические координаты q, r, s)
# ==================================================================


class HexDirection(str, Enum):
    """
    Шесть направлений гексагональной сетки (вертикальная ориентация, pointy-topped).
    """

    NORTHEAST = "northeast"
    EAST = "east"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"
    WEST = "west"
    NORTHWEST = "northwest"


HEX_DIRECTION_VECTORS: Final[dict[HexDirection, tuple[int, int, int]]] = {
    HexDirection.NORTHEAST: (1, 0, -1),
    HexDirection.EAST: (1, -1, 0),
    HexDirection.SOUTHEAST: (0, -1, 1),
    HexDirection.SOUTHWEST: (-1, 0, 1),
    HexDirection.WEST: (-1, 1, 0),
    HexDirection.NORTHWEST: (0, 1, -1),
}


# ==================================================================
# НАПРАВЛЕНИЯ ТАКТИЧЕСКОЙ СЕТКИ (2D сетка x, y)
# ==================================================================


class GridDirection(str, Enum):
    """
    Восемь направлений на прямоугольной сетке тактического боя.
    """

    NORTH = "north"
    NORTHEAST = "northeast"
    EAST = "east"
    SOUTHEAST = "southeast"
    SOUTH = "south"
    SOUTHWEST = "southwest"
    WEST = "west"
    NORTHWEST = "northwest"


GRID_DIRECTION_VECTORS: Final[dict[GridDirection, tuple[int, int]]] = {
    GridDirection.NORTH: (0, -1),
    GridDirection.NORTHEAST: (1, -1),
    GridDirection.EAST: (1, 0),
    GridDirection.SOUTHEAST: (1, 1),
    GridDirection.SOUTH: (0, 1),
    GridDirection.SOUTHWEST: (-1, 1),
    GridDirection.WEST: (-1, 0),
    GridDirection.NORTHWEST: (-1, -1),
}

CARDINAL_GRID_DIRECTIONS: Final[tuple[GridDirection, ...]] = (
    GridDirection.NORTH,
    GridDirection.EAST,
    GridDirection.SOUTH,
    GridDirection.WEST,
)

DIAGONAL_GRID_DIRECTIONS: Final[tuple[GridDirection, ...]] = (
    GridDirection.NORTHEAST,
    GridDirection.SOUTHEAST,
    GridDirection.SOUTHWEST,
    GridDirection.NORTHWEST,
)