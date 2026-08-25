"""
Тесты краевых случаев геометрии гексагональной карты: экстремальные координаты,
инварианты колец и спиралей, непрерывность линий и зонирование.
"""

import pytest

from src.back.l01_domain.exceptions.maps import InvalidCubeCoordinatesError, InvalidRadiusError
from src.back.l01_domain.maps.constants import (
    DISTANCE_BETWEEN_CITADELS_HEXES,
    STRATEGIC_MAP_TOTAL_HEXES,
    TerritoryZoneType,
)
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    determine_zone_type,
    generate_standard_map_coordinates,
    get_standard_base_coordinates,
    hex_distance,
    hex_line,
    hex_neighbors,
    hex_ring,
    hex_spiral,
)


class TestHexCoordinatesExtremeInvariants:
    def test_extreme_large_coordinates_invariant(self):
        # Огромные координаты с соблюдением q + r + s == 0
        coord = HexCoordinates(q=100000, r=-40000, s=-60000)
        assert coord.q == 100000
        assert coord.r == -40000
        assert coord.s == -60000

        target = HexCoordinates(q=-100000, r=60000, s=40000)
        dist = hex_distance(coord, target)
        # Манхэттенское расстояние: (200000 + 100000 + 100000) // 2 = 200000
        assert dist == 200000

    def test_broken_invariant_raises_domain_error(self):
        with pytest.raises(InvalidCubeCoordinatesError) as exc_info:
            HexCoordinates(q=10, r=20, s=30)  # Сумма 60 != 0

        assert exc_info.value.q == 10
        assert exc_info.value.r == 20
        assert exc_info.value.s == 30

    def test_axial_conversion_bidirectional(self):
        coord = HexCoordinates.from_axial(q=-15, r=42)
        assert coord.q == -15
        assert coord.r == 42
        assert coord.s == -27
        assert coord.to_axial() == (-15, 42)


class TestHexRingAndSpiralInvariants:
    def test_hex_ring_mathematical_properties(self):
        center = HexCoordinates.from_axial(0, 0)

        # Радиус 0 - ровно 1 гекс (центр)
        ring_0 = hex_ring(center, 0)
        assert ring_0 == [center]

        # Для любого R > 0 количество гексов в кольце строго равно 6 * R,
        # и каждый гекс находится строго на расстоянии R от центра
        for r in range(1, 6):
            ring = hex_ring(center, r)
            assert len(ring) == 6 * r
            assert len(set(ring)) == 6 * r
            for coord in ring:
                assert hex_distance(center, coord) == r

    def test_hex_spiral_mathematical_properties(self):
        center = HexCoordinates.from_axial(3, -2)

        # Количество гексов в спирали радиуса R: 1 + 3 * R * (R + 1)
        for r in range(0, 5):
            spiral = hex_spiral(center, r)
            expected_count = 1 + 3 * r * (r + 1)
            assert len(spiral) == expected_count
            assert len(set(spiral)) == expected_count
            for coord in spiral:
                assert hex_distance(center, coord) <= r

    def test_negative_radius_raises_error(self):
        center = HexCoordinates.from_axial(0, 0)
        with pytest.raises(InvalidRadiusError):
            hex_ring(center, -1)

        with pytest.raises(InvalidRadiusError):
            hex_spiral(center, -5)


class TestHexLineContinuityAndSymmetry:
    def test_line_same_point(self):
        point = HexCoordinates.from_axial(4, -8)
        assert hex_line(point, point) == [point]

    def test_line_step_by_step_continuity(self):
        start = HexCoordinates.from_axial(-4, 8)
        end = HexCoordinates.from_axial(4, -8)
        line = hex_line(start, end)

        # Длина линии = distance + 1
        expected_distance = hex_distance(start, end)
        assert len(line) == expected_distance + 1
        assert line[0] == start
        assert line[-1] == end

        # Каждый шаг строго переходит в соседний гекс (дистанция ровно 1)
        for i in range(len(line) - 1):
            assert hex_distance(line[i], line[i + 1]) == 1

    def test_standard_map_bases_distance_and_petals(self):
        north_base, south_base = get_standard_base_coordinates()
        assert hex_distance(north_base, south_base) == DISTANCE_BETWEEN_CITADELS_HEXES

        all_coords = set(generate_standard_map_coordinates())
        assert len(all_coords) == STRATEGIC_MAP_TOTAL_HEXES

        # Проверка всех 6 лепестков союзных земель вокруг каждой базы
        for base in (north_base, south_base):
            petals = hex_neighbors(base)
            assert len(petals) == 6
            for petal in petals:
                assert petal in all_coords
                assert determine_zone_type(petal, base) == TerritoryZoneType.ALLIED_LANDS
