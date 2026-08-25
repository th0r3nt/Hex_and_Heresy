"""
Исключения фракций, строительства и экономики.
"""

from typing import Optional

from src.back.l01_domain.exceptions.base import DomainError


class FactionError(DomainError):
    """
    Базовое исключение для ошибок фракций, зданий и ресурсов.
    """


class InsufficientResourcesError(FactionError):
    """
    Недостаточно ресурсов для совершения операции.
    """

    def __init__(
        self,
        resource: str,
        required: float,
        available: float,
        faction_id: Optional[str] = None,
    ) -> None:
        self.resource = resource
        self.required = required
        self.available = available
        self.faction_id = faction_id
        faction_info = f" фракции '{faction_id}'" if faction_id else ""
        super().__init__(
            f"Недостаточно ресурса '{resource}'{faction_info}: требуется {required}, доступно {available}."
        )


class NegativeResourceAmountError(FactionError):
    """
    Передано отрицательное количество ресурсов.
    """

    def __init__(self, amount: float, operation: str = "operation") -> None:
        self.amount = amount
        self.operation = operation
        super().__init__(
            f"Количество ресурса для операции '{operation}' не может быть отрицательным: получено {amount}."
        )


class BuildingMaxLevelReachedError(FactionError):
    """
    Достигнут максимальный уровень улучшения здания.
    """

    def __init__(self, building_name: str, max_level: int) -> None:
        self.building_name = building_name
        self.max_level = max_level
        super().__init__(
            f"Здание '{building_name}' уже достигло максимального уровня {max_level}."
        )


class BuildingSlotsExhaustedError(FactionError):
    """
    В зоне исчерпаны доступные строительные слоты.
    """

    def __init__(self, zone_id: str, max_slots: int) -> None:
        self.zone_id = zone_id
        self.max_slots = max_slots
        super().__init__(
            f"В зоне '{zone_id}' исчерпаны слоты для строительства: максимум {max_slots}."
        )


class ZoneNotControlledError(FactionError):
    """
    Попытка совершить действие в зоне, не подконтрольной фракции.
    """

    def __init__(self, faction_id: str, zone_id: str) -> None:
        self.faction_id = faction_id
        self.zone_id = zone_id
        super().__init__(
            f"Зона '{zone_id}' не находится под контролем фракции '{faction_id}'."
        )
