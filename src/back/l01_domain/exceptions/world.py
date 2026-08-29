"""
Исключения состояния глобального мира, трофеев и генератора новой партии.
"""

from src.back.l01_domain.exceptions.base import DomainError


class WorldStateError(DomainError):
    """
    Базовое исключение для ошибок состояния глобального мира.
    """


class BattlefieldDepletedError(WorldStateError):
    """
    Попытка мародерства на полностью истощенном или истлевшем поле брани.
    """

    def __init__(self, site_id: str) -> None:
        self.site_id = site_id
        super().__init__(f"Поле брани '{site_id}' истощено или истлело.")


class NoArmiesLockedForBattleError(WorldStateError):
    """
    Попытка выполнить тактический ход для боя, за которым не закреплено
    ни одной армии через WorldState.lock_armies_for_battle.
    """

    def __init__(self, battle_id: str) -> None:
        self.battle_id = battle_id
        super().__init__(f"За боем '{battle_id}' не закреплено ни одной армии.")


# ==================================================================
# ГЕНЕРАТОР НОВОЙ ПАРТИИ
# ==================================================================


class WorldGenerationError(DomainError):
    """
    Базовое исключение генератора мира: партию по этим настройкам собрать
    нельзя.
    """


class InvalidStartingSetupError(WorldGenerationError):
    """
    Некорректная комбинация настроек старта: непригодная для игры раса,
    партия без игрока или сразу с двумя игроками.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Некорректные настройки новой партии: {reason}")


class RulerTemplateNotFoundError(WorldGenerationError):
    """
    Запрошенный легендарный правитель отсутствует в каталоге геймдаты либо
    принадлежит другой расе.
    """

    def __init__(self, lord_id: str, race_id: str) -> None:
        self.lord_id = lord_id
        self.race_id = race_id
        super().__init__(
            f"Легендарный правитель '{lord_id}' не найден в каталоге расы '{race_id}'."
        )
