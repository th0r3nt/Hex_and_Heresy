"""
Тесты алгоритма трассировки линий Брезенхэма на 2D сетке боя,
расчета соседей и радиусов с учетом границ карты.
"""

import pytest

from src.back.l01_domain.exceptions import InvalidRadiusError
from src.back.l01_domain.maps.models.tactical import (
    CellCoordinates,
    cell_distance_chebyshev,
    cell_distance_manhattan,
    cell_line,
    cell_neighbors,
    get_cells_in_radius,
    is_within_bounds,
)


class TestBresenhamLineGeometry:
    def test_line_identical_start_and_end(self):
        point = CellCoordinates(x=5, y=5)
        assert cell_line(point, point) == [point]

    @pytest.mark.parametrize(
        ("start", "end"),
        [
            # Горизонтальные
            (CellCoordinates(x=1, y=4), CellCoordinates(x=7, y=4)),
            (CellCoordinates(x=7, y=4), CellCoordinates(x=1, y=4)),
            # Вертикальные
            (CellCoordinates(x=3, y=1), CellCoordinates(x=3, y=8)),
            (CellCoordinates(x=3, y=8), CellCoordinates(x=3, y=1)),
            # Диагонали 45 градусов
            (CellCoordinates(x=0, y=0), CellCoordinates(x=6, y=6)),
            (CellCoordinates(x=6, y=0), CellCoordinates(x=0, y=6)),
            # Пологие наклоны (|dx| > |dy|)
            (CellCoordinates(x=0, y=0), CellCoordinates(x=8, y=3)),
            (CellCoordinates(x=8, y=3), CellCoordinates(x=0, y=0)),
            # Крутые наклоны (|dy| > |dx|)
            (CellCoordinates(x=2, y=1), CellCoordinates(x=5, y=9)),
            (CellCoordinates(x=5, y=9), CellCoordinates(x=2, y=1)),
        ],
    )
    def test_bresenham_line_continuity_and_endpoints(self, start, end):
        line = cell_line(start, end)

        assert line[0] == start
        assert line[-1] == end

        # Непрерывность пути: расстояние Чебышёва между соседними клетками линии ровно 1
        for i in range(len(line) - 1):
            assert cell_distance_chebyshev(line[i], line[i + 1]) == 1


class TestTacticalGridNeighborsAndBounds:
    def test_corner_cells_neighbors_with_bounds(self):
        bounds = (14, 14)
        top_left = CellCoordinates(x=0, y=0)
        neighbors = cell_neighbors(top_left, include_diagonals=True, bounds=bounds)

        assert len(neighbors) == 3
        assert set(neighbors) == {
            CellCoordinates(x=1, y=0),
            CellCoordinates(x=0, y=1),
            CellCoordinates(x=1, y=1),
        }

    def test_edge_cells_neighbors_with_bounds(self):
        bounds = (14, 14)
        top_edge = CellCoordinates(x=5, y=0)
        neighbors = cell_neighbors(top_edge, include_diagonals=True, bounds=bounds)

        assert len(neighbors) == 5
        for n in neighbors:
            assert is_within_bounds(n, bounds[0], bounds[1])

    def test_inner_cells_neighbors_cardinal_vs_diagonals(self):
        center = CellCoordinates(x=5, y=5)
        all_8 = cell_neighbors(center, include_diagonals=True)
        cardinal_4 = cell_neighbors(center, include_diagonals=False)

        assert len(all_8) == 8
        assert len(cardinal_4) == 4
        for n in cardinal_4:
            assert n in all_8
            assert cell_distance_manhattan(center, n) == 1

    def test_get_cells_in_radius_with_boundaries(self):
        center = CellCoordinates(x=0, y=0)
        bounds = (10, 10)

        # Квадрат 3x3 с центром в (0,0), усеченный границами до 2x2 = 4 клеток
        cells = get_cells_in_radius(center, radius=1, bounds=bounds, include_diagonals=True)
        assert len(cells) == 4
        assert set(cells) == {
            CellCoordinates(x=0, y=0),
            CellCoordinates(x=1, y=0),
            CellCoordinates(x=0, y=1),
            CellCoordinates(x=1, y=1),
        }

    def test_get_cells_in_radius_negative_raises_error(self):
        center = CellCoordinates(x=5, y=5)
        with pytest.raises(InvalidRadiusError):
            get_cells_in_radius(center, radius=-1)
