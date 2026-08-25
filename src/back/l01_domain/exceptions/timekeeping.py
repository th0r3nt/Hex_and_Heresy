"""
Исключения системы летоисчисления.
"""

from src.back.l01_domain.exceptions.base import DomainError


class TimekeepingError(DomainError):
    """
    Базовое исключение для ошибок системы летоисчисления.
    """


class TimeRewindForbiddenError(TimekeepingError):
    """
    Попытка перемотать игровое время назад.
    """

    def __init__(self, ticks: int) -> None:
        self.ticks = ticks
        super().__init__(f"Нельзя перематывать игровое время назад: получено {ticks} тактов.")
