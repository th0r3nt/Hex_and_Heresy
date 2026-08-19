"""
Тесты для src/back/l01_domain/maps/models/tactical.py
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.maps.constants import GridDirection
from src.back.l01_domain.maps.models.tactical import (
    CellCoordinates,
    cell_distance_chebyshev,
    cell_distance_euclidean,
    cell_distance_manhattan,
    cell_line,
    cell_neighbor,
    cell_neighbors,
    get_cells_in_radius,
    is_within_bounds,
)


class TestCellCoordinates:
    def test_valid_coordinates(self):
        cell = CellCoordinates(x=3, y=5)
        assert cell.x == 3
        assert cell.y == 5
        assert cell.to_tuple() == (3, 5)

    def test_is_frozen(self):
        cell = CellCoordinates(x=1, y=1)
        with pytest.raises(ValidationError):
            cell.x = 2


class TestTacticalDistances:
    def test_chebyshev_distance(self):
        a = CellCoordinates(x=1, y=1)
        b = CellCoordinates(x=4, y=3)
        # max(abs(4-1), abs(3-1)) = max(3, 2) = 3
        assert cell_distance_chebyshev(a, b) == 3

    def test_manhattan_distance(self):
        a = CellCoordinates(x=1, y=1)
        b = CellCoordinates(x=4, y=3)
        # abs(4-1) + abs(3-1) = 3 + 2 = 5
        assert cell_distance_manhattan(a, b) == 5

    def test_euclidean_distance(self):
        a = CellCoordinates(x=0, y=0)
        b = CellCoordinates(x=3, y=4)
        assert cell_distance_euclidean(a, b) == pytest.approx(5.0)


class TestTacticalNavigation:
    def test_is_within_bounds(self):
        assert is_within_bounds(CellCoordinates(x=0, y=0), width=10, height=10) is True
        assert is_within_bounds(CellCoordinates(x=9, y=9), width=10, height=10) is True
        assert is_within_bounds(CellCoordinates(x=10, y=5), width=10, height=10) is False
        assert is_within_bounds(CellCoordinates(x=-1, y=5), width=10, height=10) is False

    def test_cell_neighbor(self):
        origin = CellCoordinates(x=5, y=5)
        assert cell_neighbor(origin, GridDirection.NORTH) == CellCoordinates(x=5, y=4)
        assert cell_neighbor(origin, GridDirection.SOUTHEAST) == CellCoordinates(x=6, y=6)

    def test_cell_neighbors_eight_directions(self):
        origin = CellCoordinates(x=5, y=5)
        neighbors = cell_neighbors(origin, include_diagonals=True)
        assert len(neighbors) == 8
        assert len(set(neighbors)) == 8

    def test_cell_neighbors_cardinal_only(self):
        origin = CellCoordinates(x=5, y=5)
        neighbors = cell_neighbors(origin, include_diagonals=False)
        assert len(neighbors) == 4

    def test_cell_neighbors_corner_bounded(self):
        corner = CellCoordinates(x=0, y=0)
        neighbors = cell_neighbors(corner, include_diagonals=True, bounds=(10, 10))
        assert len(neighbors) == 3
        assert set(neighbors) == {
            CellCoordinates(x=1, y=0),
            CellCoordinates(x=0, y=1),
            CellCoordinates(x=1, y=1),
        }

    def test_cell_line_bresenham(self):
        start = CellCoordinates(x=0, y=0)
        end = CellCoordinates(x=3, y=3)
        line = cell_line(start, end)

        assert line == [
            CellCoordinates(x=0, y=0),
            CellCoordinates(x=1, y=1),
            CellCoordinates(x=2, y=2),
            CellCoordinates(x=3, y=3),
        ]

    def test_get_cells_in_radius_chebyshev(self):
        center = CellCoordinates(x=5, y=5)
        # Радиус 1 по Чебышёву: квадрат 3x3 = 9 клеток
        cells = get_cells_in_radius(center, radius=1, include_diagonals=True)
        assert len(cells) == 9
        assert center in cells

    def test_get_cells_in_radius_manhattan(self):
        center = CellCoordinates(x=5, y=5)
        # Радиус 1 по Манхэттену: ромб (центр + 4 кардинала) = 5 клеток
        cells = get_cells_in_radius(center, radius=1, include_diagonals=False)
        assert len(cells) == 5
        assert center in cells
