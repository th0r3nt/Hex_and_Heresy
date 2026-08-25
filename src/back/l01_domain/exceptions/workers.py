"""
Исключения назначения рабочих отрядов.
"""

from src.back.l01_domain.exceptions.factions import FactionError


class WorkerAssignmentError(FactionError):
    """
    Базовое исключение для ошибок распределения рабочих.
    """


class WorkerNotAvailableError(WorkerAssignmentError):
    """
    Отряд недоступен для назначения.
    """

    def __init__(self, squad_id: str, reason: str) -> None:
        self.squad_id = squad_id
        self.reason = reason
        super().__init__(f"Отряд рабочих '{squad_id}' недоступен для назначения: {reason}.")


class InvalidAssignmentTargetError(WorkerAssignmentError):
    """
    Недопустимая цель для выбранного типа назначения.
    """

    def __init__(self, target: str, reason: str) -> None:
        self.target = target
        self.reason = reason
        super().__init__(f"Недопустимая цель назначения '{target}': {reason}.")


class ExpeditionRecallForbiddenError(WorkerAssignmentError):
    """
    Попытка досрочно отозвать рабочих из активной экспедиции.
    """

    def __init__(self, assignment_id: str, status: str) -> None:
        self.assignment_id = assignment_id
        self.status = status
        super().__init__(
            f"Невозможно отозвать экспедицию '{assignment_id}': досрочный возврат в статусе '{status}' запрещен."
        )


class BuildingWorkerCapacityExceededError(WorkerAssignmentError):
    """
    В здании нет свободных мест для рабочих.
    """

    def __init__(self, building_id: str, max_capacity: int) -> None:
        self.building_id = building_id
        self.max_capacity = max_capacity
        super().__init__(
            f"В здании '{building_id}' исчерпан лимит рабочих мест (максимум {max_capacity})."
        )
