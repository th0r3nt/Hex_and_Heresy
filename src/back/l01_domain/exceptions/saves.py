"""
Исключения операций сохранения и загрузки партии.
"""

from src.back.l01_domain.exceptions.base import DomainError


class SaveGameError(DomainError):
    """
    Базовое исключение для операций сохранения и загрузки партии.
    """


class SaveNotFoundError(SaveGameError):
    """
    Запрошенное сохранение отсутствует в хранилище.
    """

    def __init__(self, save_id: str) -> None:
        self.save_id = save_id
        super().__init__(f"Сохранение с ID '{save_id}' не найдено в хранилище.")


class SaveDataCorruptedError(SaveGameError):
    """
    Снимок партии не восстанавливается: структура данных повреждена или устарела.
    """

    def __init__(self, save_id: str, reason: str) -> None:
        self.save_id = save_id
        self.reason = reason
        super().__init__(f"Сохранение '{save_id}' повреждено и не может быть загружено: {reason}.")


class SaveDuringBattleForbiddenError(SaveGameError):
    """
    Попытка сохранить партию, пока не завершен тактический бой.
    """

    def __init__(self, battle_ids: list[str]) -> None:
        self.battle_ids = battle_ids
        battles = ", ".join(f"'{bid}'" for bid in battle_ids)
        super().__init__(
            f"Сохранение запрещено до завершения тактических боев: {battles}."
        )


class EmptySaveNameError(SaveGameError):
    """
    Передано пустое имя сохранения.
    """

    def __init__(self) -> None:
        super().__init__("Имя сохранения не может быть пустым.")
