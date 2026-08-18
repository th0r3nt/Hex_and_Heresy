"""
Константы и перечисления геометрии карт: направления, зонирование и радиусы.
"""

from enum import Enum
from typing import Final

# ==================================================================
# ЗОНИРОВАНИЕ ТЕРРИТОРИЙ
# ==================================================================


class TerritoryZoneType(str, Enum):
    """
    Тип зоны гексагональной карты.
    """

    BASE = "base"
    ALLIED_LANDS = "allied_lands"
    NEUTRAL_LANDS = "neutral_lands"


ALLIED_LANDS_RING_RADIUS: Final[int] = 1
NEUTRAL_LANDS_DEPTH: Final[int] = 2
MAX_GLOBAL_MAP_RADIUS: Final[int] = 3


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
