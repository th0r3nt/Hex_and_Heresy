"""
Исключения механики летописца и зала павших.
"""

from src.back.l01_domain.exceptions.base import DomainError


class ChroniclerError(DomainError):
    """
    Базовое исключение механики летописца.
    """


class BattleDossierNotFoundError(ChroniclerError):
    """
    Летописец не заводил досье на этот бой.

    Означает пропущенное начало боя: летописец копит числа с первого раунда,
    и без стартового снимка сторон пересказывать нечего.
    """

    def __init__(self, battle_id: str) -> None:
        self.battle_id = battle_id
        super().__init__(f"Летописец не ведет досье боя '{battle_id}': его начало не зафиксировано.")


class ChronicleGenerationFailedError(ChroniclerError):
    """
    Летопись или некролог не сгенерированы: языковая модель недоступна или
    вернула пустой текст.
    """

    def __init__(self, battle_id: str, reason: str) -> None:
        self.battle_id = battle_id
        self.reason = reason
        super().__init__(f"Летопись боя '{battle_id}' не составлена: {reason}.")
