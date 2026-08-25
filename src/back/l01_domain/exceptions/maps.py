"""
Исключения координат и геометрии карт.
"""

from src.back.l01_domain.exceptions.base import DomainError


class MapGeometryError(DomainError):
    """
    Базовое исключение для ошибок координат и геометрии карт.
    """


class InvalidCubeCoordinatesError(MapGeometryError):
    """
    Нарушен кубический инвариант гексагональной сетки q + r + s == 0.
    """

    def __init__(self, q: int, r: int, s: int) -> None:
        self.q = q
        self.r = r
        self.s = s
        super().__init__(
            f"Нарушен инвариант кубических координат: q({q}) + r({r}) + s({s}) = {q + r + s} != 0."
        )


class HexOutOfBoundsError(MapGeometryError):
    """
    Гекс находится за пределами допустимой глобальной карты.
    """

    def __init__(self, q: int, r: int, s: int) -> None:
        self.q = q
        self.r = r
        self.s = s
        super().__init__(f"Гекс с координатами ({q}, {r}, {s}) находится за пределами карты.")


class InvalidRadiusError(MapGeometryError):
    """
    Передан отрицательный радиус кольца или спирали.
    """

    def __init__(self, radius: int) -> None:
        self.radius = radius
        super().__init__(f"Радиус должен быть неотрицательным числом: получено {radius}.")
