"""
Корень иерархии доменных исключений проекта Hex & Heresy.
"""


class DomainError(Exception):
    """Базовый класс для всех исключений доменного слоя."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
