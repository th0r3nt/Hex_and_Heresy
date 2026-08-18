"""
Тесты для src/back/l01_domain/maps/constants.py
"""

from src.back.l01_domain.maps.constants import (
    ALLIED_LANDS_RING_RADIUS,
    CARDINAL_GRID_DIRECTIONS,
    DIAGONAL_GRID_DIRECTIONS,
    DISTANCE_BETWEEN_CITADELS_HEXES,
    GLOBAL_MAP_ROW_LENGTHS,
    GLOBAL_MAP_TOTAL_HEXES,
    GLOBAL_MAP_TOTAL_ROWS,
    GRID_DIRECTION_VECTORS,
    HEX_DIRECTION_VECTORS,
    HEX_SCALE_KM,
    GridDirection,
    HexDirection,
    TerritoryZoneType,
)


def test_hex_directions_count_and_vectors():
    assert len(HexDirection) == 6
    assert len(HEX_DIRECTION_VECTORS) == 6
    for direction, (dq, dr, ds) in HEX_DIRECTION_VECTORS.items():
        assert dq + dr + ds == 0, f"Hex vector for {direction} violates cube invariant"


def test_grid_directions_count_and_vectors():
    assert len(GridDirection) == 8
    assert len(GRID_DIRECTION_VECTORS) == 8
    assert len(CARDINAL_GRID_DIRECTIONS) == 4
    assert len(DIAGONAL_GRID_DIRECTIONS) == 4


def test_territory_zone_types_defined():
    assert TerritoryZoneType.BASE == "base"
    assert TerritoryZoneType.ALLIED_LANDS == "allied_lands"
    assert TerritoryZoneType.NEUTRAL_LANDS == "neutral_lands"


def test_standard_map_constants():
    assert GLOBAL_MAP_TOTAL_ROWS == 19
    assert len(GLOBAL_MAP_ROW_LENGTHS) == 19
    assert sum(GLOBAL_MAP_ROW_LENGTHS) == 271
    assert GLOBAL_MAP_TOTAL_HEXES == 271
    assert HEX_SCALE_KM == 7.5
    assert ALLIED_LANDS_RING_RADIUS == 1
    assert DISTANCE_BETWEEN_CITADELS_HEXES == 16
