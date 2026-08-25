"""
Исключения тактического боя.
"""

from src.back.l01_domain.exceptions.base import DomainError


class CombatError(DomainError):
    """
    Базовое исключение для ошибок тактического боя.
    """


class InvalidBattlePhaseError(CombatError):
    """
    Действие недопустимо в текущей фазе боя.
    """

    def __init__(self, current_phase: str, attempted_action: str) -> None:
        self.current_phase = current_phase
        self.attempted_action = attempted_action
        super().__init__(
            f"Действие '{attempted_action}' недопустимо в фазе боя '{current_phase}'."
        )


class CellOutOfBoundsError(CombatError):
    """
    Координаты клетки выходят за пределы сетки боя.
    """

    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        super().__init__(
            f"Клетка ({x}, {y}) выходит за пределы поля боя размером {width}x{height}."
        )


class CellOccupiedError(CombatError):
    """
    Попытка занять уже занятую клетку.
    """

    def __init__(self, x: int, y: int, occupant_id: str) -> None:
        self.x = x
        self.y = y
        self.occupant_id = occupant_id
        super().__init__(f"Клетка ({x}, {y}) уже занята отрядом '{occupant_id}'.")


class OrderNotAllowedError(CombatError):
    """
    Приказ не может быть выполнен отрядом (например, в состоянии паники).
    """

    def __init__(self, squad_id: str, reason: str) -> None:
        self.squad_id = squad_id
        self.reason = reason
        super().__init__(f"Приказ отряду '{squad_id}' отклонен: {reason}.")


class InvalidReactionError(CombatError):
    """
    Выбрана недопустимая реакция на натиск.
    """

    def __init__(self, reaction: str, reason: str) -> None:
        self.reaction = reaction
        self.reason = reason
        super().__init__(f"Реакция '{reaction}' недопустима: {reason}.")
