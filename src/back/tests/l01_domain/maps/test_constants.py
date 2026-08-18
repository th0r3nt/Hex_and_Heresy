"""
Тесты для src/back/l01_domain/maps/constants.py
"""

from src.back.l01_domain.maps.constants import (
    CARDINAL_GRID_DIRECTIONS,
    DIAGONAL_GRID_DIRECTIONS,
    GRID_DIRECTION_VECTORS,
    HEX_DIRECTION_VECTORS,
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
