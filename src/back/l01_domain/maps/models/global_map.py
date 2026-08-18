"""
Геометрия глобальной гексагональной карты: кубические координаты,
расстояния, соседство, кольца, спирали и линейная интерполяция.
"""

from pydantic import BaseModel, Field, ConfigDict, model_validator

from src.back.l01_domain.maps.constants import (
    ALLIED_LANDS_RING_RADIUS,
    HEX_DIRECTION_VECTORS,
    HexDirection,
    TerritoryZoneType,
)


class HexCoordinates(BaseModel):
    """
    Кубические координаты гексагона (q, r, s).
    Гарантирует математический инвариант: q + r + s == 0.
    """

    model_config = ConfigDict(frozen=True)

    q: int = Field(..., description="Координата q (ось /)")
    r: int = Field(..., description="Координата r (ось —)")
    s: int = Field(..., description="Координата s (ось \\)")

    @model_validator(mode="after")
    def validate_cube_invariant(self) -> "HexCoordinates":
        if self.q + self.r + self.s != 0:
            raise ValueError(
                f"cube coordinates invariant violated: q({self.q}) + r({self.r}) + s({self.s}) != 0"
            )
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
        raise ValueError(f"radius must be non-negative, got {radius}")
    if radius == 0:
        return [center]

    results: list[HexCoordinates] = []
    # Начинаем с западного направления, смещаясь на радиус
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
        raise ValueError(f"max_radius must be non-negative, got {max_radius}")

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
    # Добавляем небольшое смещение для детерминированного округления на ребрах
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


def determine_zone_type(
    coord: HexCoordinates, base_coord: HexCoordinates
) -> TerritoryZoneType:
    """
    Определяет категорию территории относительно базы фракции.
    """
    
    distance = hex_distance(coord, base_coord)
    if distance == 0:
        return TerritoryZoneType.BASE
    if distance <= ALLIED_LANDS_RING_RADIUS:
        return TerritoryZoneType.ALLIED_LANDS
    return TerritoryZoneType.NEUTRAL_LANDS
