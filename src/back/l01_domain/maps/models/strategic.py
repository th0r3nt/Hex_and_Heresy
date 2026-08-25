"""
Геометрия глобальной гексагональной карты: кубические координаты,
расстояния, соседство, генерация 271-гексагонной сетки и зонирование.
"""

from typing import Union
from pydantic import BaseModel, Field, ConfigDict, model_validator

from src.back.l01_domain.maps.constants import (
    ALLIED_LANDS_RING_RADIUS,
    STRATEGIC_MAP_ROW_LENGTHS,
    STRATEGIC_MAP_TOTAL_HEXES,
    STRATEGIC_MAP_TOTAL_ROWS,
    HEX_DIRECTION_VECTORS,
    HexDirection,
    TerritoryZoneType,
)

from src.back.l01_domain.exceptions.maps import InvalidCubeCoordinatesError, InvalidRadiusError


class HexCoordinates(BaseModel):
    """
    Кубические координаты гексагона (q, r, s).
    Гарантирует математический инвариант: q + r + s == 0.
    """

    model_config = ConfigDict(frozen=True)

    q: int = Field(..., description="Координата q (ось /)")
    r: int = Field(..., description="Координата r (ось -)")
    s: int = Field(..., description="Координата s (ось \\)")

    @model_validator(mode="after")
    def validate_cube_invariant(self) -> "HexCoordinates":
        if self.q + self.r + self.s != 0:
            raise InvalidCubeCoordinatesError(self.q, self.r, self.s)
        return self

    @classmethod
    def from_axial(cls, q: int, r: int) -> "HexCoordinates":
        """
        Создает кубические координаты из пары осевых (q, r).
        """
        return cls(q=q, r=r, s=-q - r)

    def to_axial(self) -> tuple[int, int]:
        """
        Возвращает пару осевых координат (q, r).
        """
        return (self.q, self.r)


# ==================================================================
# ЧИСТЫЕ ГЕОМЕТРИЧЕСКИЕ ФУНКЦИИ
# ==================================================================


def hex_distance(a: HexCoordinates, b: HexCoordinates) -> int:
    """
    Манхэттенское расстояние между двумя гексами на кубической сетке.
    """
    return (abs(a.q - b.q) + abs(a.r - b.r) + abs(a.s - b.s)) // 2


def hex_neighbor(coord: HexCoordinates, direction: HexDirection) -> HexCoordinates:
    """
    Возвращает координаты соседнего гекса в заданном направлении.
    """
    dq, dr, ds = HEX_DIRECTION_VECTORS[direction]
    return HexCoordinates(q=coord.q + dq, r=coord.r + dr, s=coord.s + ds)


def hex_neighbors(coord: HexCoordinates) -> list[HexCoordinates]:
    """
    Возвращает список всех шести соседних гексов.
    """
    return [hex_neighbor(coord, direction) for direction in HexDirection]


def hex_ring(center: HexCoordinates, radius: int) -> list[HexCoordinates]:
    """
    Возвращает координаты замкнутого кольца гексов заданного радиуса.
    """
    if radius < 0:
        raise InvalidRadiusError(radius)
    if radius == 0:
        return [center]

    results: list[HexCoordinates] = []
    west_vector = HEX_DIRECTION_VECTORS[HexDirection.WEST]
    current = HexCoordinates(
        q=center.q + west_vector[0] * radius,
        r=center.r + west_vector[1] * radius,
        s=center.s + west_vector[2] * radius,
    )

    ordered_directions = (
        HexDirection.NORTHEAST,
        HexDirection.EAST,
        HexDirection.SOUTHEAST,
        HexDirection.SOUTHWEST,
        HexDirection.WEST,
        HexDirection.NORTHWEST,
    )

    for direction in ordered_directions:
        dq, dr, ds = HEX_DIRECTION_VECTORS[direction]
        for _ in range(radius):
            results.append(current)
            current = HexCoordinates(q=current.q + dq, r=current.r + dr, s=current.s + ds)

    return results


def hex_spiral(center: HexCoordinates, max_radius: int) -> list[HexCoordinates]:
    """
    Возвращает список всех координат в пределах радиуса max_radius от центра (включая центр).
    """
    if max_radius < 0:
        raise InvalidRadiusError(max_radius)

    results: list[HexCoordinates] = []
    for r in range(max_radius + 1):
        results.extend(hex_ring(center, r))
    return results


def _cube_round(frac_q: float, frac_r: float, frac_s: float) -> HexCoordinates:
    """
    Округление дробных кубических координат до ближайшего целочисленного гекса.
    """
    q = round(frac_q)
    r = round(frac_r)
    s = round(frac_s)

    q_diff = abs(q - frac_q)
    r_diff = abs(r - frac_r)
    s_diff = abs(s - frac_s)

    if q_diff > r_diff and q_diff > s_diff:
        q = -r - s
    elif r_diff > s_diff:
        r = -q - s
    else:
        s = -q - r

    return HexCoordinates(q=q, r=r, s=s)


def hex_line(start: HexCoordinates, end: HexCoordinates) -> list[HexCoordinates]:
    """
    Линейная интерполяция между двумя гексами (трассировка пути).
    """
    distance = hex_distance(start, end)
    if distance == 0:
        return [start]

    results: list[HexCoordinates] = []
    nudge_q = 1e-6
    nudge_r = 1e-6
    nudge_s = -2e-6

    start_q = start.q + nudge_q
    start_r = start.r + nudge_r
    start_s = start.s + nudge_s

    for i in range(distance + 1):
        t = i / distance
        curr_q = start_q * (1.0 - t) + (end.q + nudge_q) * t
        curr_r = start_r * (1.0 - t) + (end.r + nudge_r) * t
        curr_s = start_s * (1.0 - t) + (end.s + nudge_s) * t
        results.append(_cube_round(curr_q, curr_r, curr_s))

    return results


# ==================================================================
# ГЕНЕРАЦИЯ СТАНДАРТНОЙ КАРТЫ (271 гекс)
# ==================================================================


def get_standard_base_coordinates() -> tuple[HexCoordinates, HexCoordinates]:
    """
    Возвращает кубические координаты Северной (красной) и Южной (синей) цитаделей.
    """
    north_base = HexCoordinates.from_axial(4, -8)  # ряд 1 в SVG
    south_base = HexCoordinates.from_axial(-4, 8)  # ряд 17 в SVG
    return north_base, south_base


def generate_standard_map_coordinates() -> list[HexCoordinates]:
    """
    Генерирует полный список из 271 кубической координаты для стандартной карты (19 рядов).
    Математически и позиционно строго соответствует раскладке map.svg.
    """
    coordinates: list[HexCoordinates] = []
    center_row = STRATEGIC_MAP_TOTAL_ROWS // 2  # ряд 9 (экватор r = 0)

    for row_idx, row_len in enumerate(STRATEGIC_MAP_ROW_LENGTHS):
        r = row_idx - center_row
        half_len = (row_len - 1) / 2.0

        for col_idx in range(row_len):
            offset_from_center = col_idx - half_len
            q = int(offset_from_center - r / 2.0)
            coordinates.append(HexCoordinates.from_axial(q, r))

    if len(coordinates) != STRATEGIC_MAP_TOTAL_HEXES:
        raise RuntimeError(
            f"ошибка генерации карты: ожидался {STRATEGIC_MAP_TOTAL_HEXES} гекс, получено {len(coordinates)}"
        )

    return coordinates


def determine_zone_type(
    coord: HexCoordinates,
    base_coords: Union[HexCoordinates, list[HexCoordinates]],
) -> TerritoryZoneType:
    """
    Определяет категорию территории относительно одной или нескольких баз.
    """
    bases = [base_coords] if isinstance(base_coords, HexCoordinates) else base_coords

    min_distance = min(hex_distance(coord, base) for base in bases)

    if min_distance == 0:
        return TerritoryZoneType.BASE
    if min_distance <= ALLIED_LANDS_RING_RADIUS:
        return TerritoryZoneType.ALLIED_LANDS
    return TerritoryZoneType.NEUTRAL_LANDS
