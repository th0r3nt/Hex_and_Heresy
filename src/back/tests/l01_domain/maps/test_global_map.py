"""
Тесты для src/back/l01_domain/maps/models/global.py
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.maps.constants import HexDirection, TerritoryZoneType
from src.back.l01_domain.maps.models.global_map import (
    HexCoordinates,
    determine_zone_type,
    hex_distance,
    hex_line,
    hex_neighbor,
    hex_neighbors,
    hex_ring,
    hex_spiral,
)


class TestHexCoordinates:
    def test_valid_cube_coordinates(self):
        coord = HexCoordinates(q=1, r=-2, s=1)
        assert coord.q == 1
        assert coord.r == -2
        assert coord.s == 1

    def test_invalid_cube_coordinates_raise_error(self):
        with pytest.raises(ValidationError):
            HexCoordinates(q=1, r=1, s=1)

    def test_from_axial_factory(self):
        coord = HexCoordinates.from_axial(q=2, r=-3)
        assert coord.q == 2
        assert coord.r == -3
        assert coord.s == 1
        assert coord.to_axial() == (2, -3)

    def test_is_frozen(self):
        coord = HexCoordinates.from_axial(0, 0)
        with pytest.raises(ValidationError):
            coord.q = 1


class TestHexMath:
    def test_hex_distance_same_point(self):
        origin = HexCoordinates.from_axial(0, 0)
        assert hex_distance(origin, origin) == 0

    def test_hex_distance_neighbors(self):
        origin = HexCoordinates.from_axial(0, 0)
        neighbor = HexCoordinates.from_axial(1, 0)
        assert hex_distance(origin, neighbor) == 1

    def test_hex_distance_arbitrary(self):
        a = HexCoordinates.from_axial(-2, 3)
        b = HexCoordinates.from_axial(2, -1)
        # dq = 4, dr = -4, ds = 0 -> distance = (4 + 4 + 0) // 2 = 4
        assert hex_distance(a, b) == 4

    def test_hex_neighbors_count_and_distance(self):
        origin = HexCoordinates.from_axial(0, 0)
        neighbors = hex_neighbors(origin)

        assert len(neighbors) == 6
        assert len(set(neighbors)) == 6
        for n in neighbors:
            assert hex_distance(origin, n) == 1

    def test_hex_neighbor_specific_direction(self):
        origin = HexCoordinates.from_axial(0, 0)
        ne = hex_neighbor(origin, HexDirection.NORTHEAST)
        assert ne == HexCoordinates(q=1, r=0, s=-1)

    def test_hex_ring_radius_zero(self):
        origin = HexCoordinates.from_axial(0, 0)
        ring = hex_ring(origin, 0)
        assert ring == [origin]

    def test_hex_ring_radius_one(self):
        origin = HexCoordinates.from_axial(0, 0)
        ring = hex_ring(origin, 1)

        assert len(ring) == 6
        assert len(set(ring)) == 6
        for coord in ring:
            assert hex_distance(origin, coord) == 1

    def test_hex_ring_radius_two(self):
        origin = HexCoordinates.from_axial(0, 0)
        ring = hex_ring(origin, 2)

        assert len(ring) == 12
        assert len(set(ring)) == 12
        for coord in ring:
            assert hex_distance(origin, coord) == 2

    def test_hex_ring_negative_radius_raises(self):
        origin = HexCoordinates.from_axial(0, 0)
        with pytest.raises(ValueError):
            hex_ring(origin, -1)

    def test_hex_spiral_radius_three_matches_svg_map_size(self):
        # 1 + 6 + 12 + 18 = 37 гексов (ровно как в map.svg)
        origin = HexCoordinates.from_axial(0, 0)
        spiral = hex_spiral(origin, 3)

        assert len(spiral) == 37
        assert len(set(spiral)) == 37

    def test_hex_line_single_cell(self):
        origin = HexCoordinates.from_axial(1, 1)
        assert hex_line(origin, origin) == [origin]

    def test_hex_line_straight(self):
        start = HexCoordinates.from_axial(0, 0)
        end = HexCoordinates.from_axial(3, 0)
        line = hex_line(start, end)

        assert len(line) == 4
        assert line[0] == start
        assert line[-1] == end
        assert line == [
            HexCoordinates.from_axial(0, 0),
            HexCoordinates.from_axial(1, 0),
            HexCoordinates.from_axial(2, 0),
            HexCoordinates.from_axial(3, 0),
        ]


class TestZoneDetermination:
    def test_base_zone(self):
        base = HexCoordinates.from_axial(0, 0)
        assert determine_zone_type(base, base) == TerritoryZoneType.BASE

    def test_allied_zone(self):
        base = HexCoordinates.from_axial(0, 0)
        allied_hex = HexCoordinates.from_axial(1, -1)
        assert determine_zone_type(allied_hex, base) == TerritoryZoneType.ALLIED_LANDS

    def test_neutral_zone(self):
        base = HexCoordinates.from_axial(0, 0)
        neutral_hex = HexCoordinates.from_axial(2, 0)
        assert determine_zone_type(neutral_hex, base) == TerritoryZoneType.NEUTRAL_LANDS