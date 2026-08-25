"""
Исключения армии, отрядов и персонажей.
"""

from typing import Optional

from src.back.l01_domain.exceptions.base import DomainError


class ArmyError(DomainError):
    """
    Базовое исключение для ошибок армии, отрядов и персонажей.
    """


class SquadDepletedError(ArmyError):
    """
    Попытка совершить действие с уже полностью уничтоженным отрядом.
    """

    def __init__(self, squad_id: str) -> None:
        self.squad_id = squad_id
        super().__init__(f"Отряд '{squad_id}' полностью уничтожен и не может действовать.")


class InvalidEquipmentSlotError(ArmyError):
    """
    Предмет экипировки не соответствует целевому слоту.
    """

    def __init__(self, item_id: str, expected_slot: str, actual_slot: str) -> None:
        self.item_id = item_id
        self.expected_slot = expected_slot
        self.actual_slot = actual_slot
        super().__init__(
            f"Предмет '{item_id}' слота '{actual_slot}' не подходит для слота '{expected_slot}'."
        )


class HeroLevelTooLowError(ArmyError):
    """
    Уровень героя недостаточен для изучения выбранного перка.
    """

    def __init__(
        self, current_level: int, required_level: int, perk_id: Optional[str] = None
    ) -> None:
        self.current_level = current_level
        self.required_level = required_level
        self.perk_id = perk_id
        perk_info = f" перка '{perk_id}'" if perk_id else " перка"
        super().__init__(
            f"Уровень героя {current_level} слишком мал для изучения{perk_info}, требующего уровень {required_level}."
        )


class HeroAlreadyWoundedError(ArmyError):
    """
    Попытка применить тяжелое ранение к герою, который уже выбыл из строя.
    """

    def __init__(self, hero_id: str) -> None:
        self.hero_id = hero_id
        super().__init__(f"Герой '{hero_id}' уже находится в состоянии тяжелого ранения.")


class NegativeExperienceError(ArmyError):
    """
    Попытка передать отрицательное значение опыта.
    """

    def __init__(self, amount: int) -> None:
        self.amount = amount
        super().__init__(f"Количество опыта не может быть отрицательным: получено {amount}.")


class CommanderAlreadyAssignedError(ArmyError):
    """
    Полководец уже назначен командовать другой армией.
    """

    def __init__(self, commander_id: str, current_army_id: str) -> None:
        self.commander_id = commander_id
        self.current_army_id = current_army_id
        super().__init__(
            f"Полководец '{commander_id}' уже командует армией '{current_army_id}'."
        )
