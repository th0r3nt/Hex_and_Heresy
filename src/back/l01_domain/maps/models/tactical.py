"""
Геометрия тактической прямоугольной сетки: координаты клеток,
метрики расстояний, соседи, проверка границ и трассировка луча Брезенхэма.
"""

import math
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.maps.constants import (
    CARDINAL_GRID_DIRECTIONS,
    GRID_DIRECTION_VECTORS,
    GridDirection,
)

from src.back.l01_domain.exceptions.maps import InvalidRadiusError

class CellCoordinates(BaseModel):
    """
    Координаты клетки на тактической сетке боя (x, y).
    """

    model_config = ConfigDict(frozen=True)

    x: int = Field(..., description="Координата X (колонка, от 0)")
    y: int = Field(..., description="Координата Y (строка, от 0)")

    def to_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)


# ==================================================================
# МЕТРИКИ РАССТОЯНИЙ
# ==================================================================


def cell_distance_chebyshev(a: CellCoordinates, b: CellCoordinates) -> int:
    """
    Расстояние Чебышёва (максимум разностей по осям).
    Используется для перемещения отрядов при свободном ходе в 8 направлениях.
    """
    return max(abs(a.x - b.x), abs(a.y - b.y))


def cell_distance_manhattan(a: CellCoordinates, b: CellCoordinates) -> int:
    """
    Манхэттенское расстояние (сумма разностей по осям).
    Используется при расчёте движения строго по 4 кардинальным направлениям.
    """
    return abs(a.x - b.x) + abs(a.y - b.y)


def cell_distance_euclidean(a: CellCoordinates, b: CellCoordinates) -> float:
    """
    Евклидово расстояние.
    Используется для проверки радиусов аур, взрывов и баллистики.
    """
    return math.hypot(a.x - b.x, a.y - b.y)


# ==================================================================
# НАВИГАЦИЯ И СОСЕДСТВО
# ==================================================================


def is_within_bounds(coord: CellCoordinates, width: int, height: int) -> bool:
    """
    Проверяет, лежит ли клетка внутри прямоугольного поля [0, width) x [0, height).
    """
    return 0 <= coord.x < width and 0 <= coord.y < height


def cell_neighbor(coord: CellCoordinates, direction: GridDirection) -> CellCoordinates:
    """
    Возвращает координаты соседней клетки в указанном направлении.
    """
    dx, dy = GRID_DIRECTION_VECTORS[direction]
    return CellCoordinates(x=coord.x + dx, y=coord.y + dy)


def cell_neighbors(
    coord: CellCoordinates,
    include_diagonals: bool = True,
    bounds: Optional[tuple[int, int]] = None,
) -> list[CellCoordinates]:
    """
    Возвращает список соседних клеток.
    include_diagonals: True - 8 направлений, False - 4 кардинальных направления.
    bounds: опциональный кортеж (width, height) для фильтрации вышедших за границу клеток.
    """
    directions = list(GridDirection) if include_diagonals else list(CARDINAL_GRID_DIRECTIONS)
    neighbors: list[CellCoordinates] = []

    for direction in directions:
        next_cell = cell_neighbor(coord, direction)
        if bounds is not None and not is_within_bounds(next_cell, bounds[0], bounds[1]):
            continue
        neighbors.append(next_cell)

    return neighbors


def cell_line(start: CellCoordinates, end: CellCoordinates) -> list[CellCoordinates]:
    """
    Построение линии клеток между двумя точками алгоритмом Брезенхэма.
    Используется для проверки линии видимости и препятствий (укрытий).
    """
    x0, y0 = start.x, start.y
    x1, y1 = end.x, end.y

    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    cells: list[CellCoordinates] = []

    while True:
        cells.append(CellCoordinates(x=x0, y=y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy

    return cells


def get_cells_in_radius(
    center: CellCoordinates,
    radius: int,
    bounds: Optional[tuple[int, int]] = None,
    include_diagonals: bool = True,
) -> list[CellCoordinates]:
    """
    Возвращает все клетки в пределах заданного радиуса (включая центральную).
    """
    
    if radius < 0:
        raise InvalidRadiusError(radius)

    results: list[CellCoordinates] = []
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if not include_diagonals and (abs(dx) + abs(dy) > radius):
                continue
            if include_diagonals and max(abs(dx), abs(dy)) > radius:
                continue

            cell = CellCoordinates(x=center.x + dx, y=center.y + dy)
            if bounds is not None and not is_within_bounds(cell, bounds[0], bounds[1]):
                continue
            results.append(cell)

    return results
