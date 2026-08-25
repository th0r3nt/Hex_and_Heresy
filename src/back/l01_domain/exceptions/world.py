"""
Исключения состояния глобального мира и трофеев.
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
