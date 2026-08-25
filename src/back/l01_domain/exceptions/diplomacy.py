"""
Исключения дипломатических конфликтов и соглашений.
"""

from src.back.l01_domain.exceptions.factions import FactionError


class DiplomacyError(FactionError):
    """
    Базовое исключение для дипломатических конфликтов и соглашений.
    """


class PactForbiddenDuringWarError(DiplomacyError):
    """
    Запрет на заключение мирных пактов во время войны.
    """

    def __init__(self, pact_name: str, faction_a_id: str, faction_b_id: str) -> None:
        self.pact_name = pact_name
        self.faction_a_id = faction_a_id
        self.faction_b_id = faction_b_id
        super().__init__(
            f"Невозможно заключить пакт '{pact_name}' между фракциями '{faction_a_id}' и '{faction_b_id}' в состоянии войны."
        )


class WarAllianceWithEnemyForbiddenError(DiplomacyError):
    """
    Попытка создать военный союз с фракцией, с которой уже идет война.
    """

    def __init__(self, faction_a_id: str, faction_b_id: str) -> None:
        self.faction_a_id = faction_a_id
        self.faction_b_id = faction_b_id
        super().__init__(
            f"Невозможно заключить военный союз с фракцией '{faction_b_id}', так как с ней объявлена война."
        )


class DiplomaticRelationNotFoundError(DiplomacyError):
    """
    Отношения между указанными фракциями не найдены в реестре.
    """

    def __init__(self, faction_a_id: str, faction_b_id: str) -> None:
        self.faction_a_id = faction_a_id
        self.faction_b_id = faction_b_id
        super().__init__(
            f"Дипломатические отношения между фракциями '{faction_a_id}' и '{faction_b_id}' не найдены."
        )


class AmbassadorUnavailableError(DiplomacyError):
    """
    Посол недоступен для аудиенции или отправки.
    """

    def __init__(self, ambassador_id: str, status: str) -> None:
        self.ambassador_id = ambassador_id
        self.status = status
        super().__init__(f"Посол '{ambassador_id}' недоступен: текущий статус '{status}'.")


class SelfDiplomacyForbiddenError(DiplomacyError):
    """
    Попытка отправить депешу или посла самому себе.
    """

    def __init__(self, faction_id: str) -> None:
        self.faction_id = faction_id
        super().__init__(
            f"Фракция '{faction_id}' не может вести дипломатию сама с собой."
        )


class FactionCapitalUnknownError(DiplomacyError):
    """
    У фракции не задан гекс цитадели, поэтому маршрут гонца или посла не построить.
    """

    def __init__(self, faction_id: str) -> None:
        self.faction_id = faction_id
        super().__init__(f"У фракции '{faction_id}' не задан гекс цитадели (capital_hex).")
