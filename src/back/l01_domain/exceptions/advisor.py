"""
Исключения механики советника.
"""

from src.back.l01_domain.exceptions.base import DomainError


class AdvisorError(DomainError):
    """
    Базовое исключение механики советника.
    """


class AdvisorDisabledError(AdvisorError):
    """
    Советник выключен игроком в настройках партии.

    Пассивные предложения при этом просто не рождаются, а вот прямое
    обращение к выключенному советнику - ошибка запроса: интерфейс не должен
    открывать окно, которого нет.
    """

    def __init__(self) -> None:
        super().__init__(
            "Советник отключен в настройках партии: включите его, чтобы получать советы."
        )


class AdvisorProposalNotFoundError(AdvisorError):
    """
    Предложение не найдено: игрок уже ответил на него или партия перезапущена.
    """

    def __init__(self, proposal_id: str) -> None:
        self.proposal_id = proposal_id
        super().__init__(
            f"Предложение советника '{proposal_id}' не найдено: оно уже закрыто или устарело."
        )


class AdvisorOptionNotFoundError(AdvisorError):
    """
    Игрок выбрал вариант, которого советник не предлагал.
    """

    def __init__(self, proposal_id: str, option_id: str) -> None:
        self.proposal_id = proposal_id
        self.option_id = option_id
        super().__init__(
            f"В предложении '{proposal_id}' нет варианта ответа '{option_id}'."
        )


class AdvisorGenerationFailedError(AdvisorError):
    """
    Советник промолчал: языковая модель недоступна или вернула пустой текст.
    """

    def __init__(self, faction_id: str, reason: str) -> None:
        self.faction_id = faction_id
        self.reason = reason
        super().__init__(f"Советник фракции '{faction_id}' не ответил: {reason}.")
