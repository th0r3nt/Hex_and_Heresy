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


class FactionNotFoundError(FactionError):
    """
    Фракции с указанным идентификатором нет в текущей партии.
    """

    def __init__(self, faction_id: str) -> None:
        self.faction_id = faction_id
        super().__init__(f"Фракция '{faction_id}' не найдена в текущей партии.")


class InvalidTaxRateError(FactionError):
    """
    Налоговая ставка вышла за допустимые границы ползунка.
    """

    def __init__(self, rate: float, min_rate: float, max_rate: float) -> None:
        self.rate = rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        super().__init__(
            f"Налоговая ставка {rate} вне допустимого диапазона [{min_rate}, {max_rate}]."
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


# ====================================================
# Гарнизоны земель
# ====================================================


class GarrisonNotFoundError(FactionError):
    """
    На указанной земле нет гарнизона: землю не контролируют либо
    административный центр там еще не построен.
    """

    def __init__(self, zone_id: str) -> None:
        self.zone_id = zone_id
        super().__init__(f"Гарнизон земли '{zone_id}' не найден.")


class GarrisonCapacityExceededError(FactionError):
    """
    Превышен лимит расквартированных войск: земля вмещает ровно
    MAX_STATIONED_GARRISON_SQUADS карточек.
    """

    def __init__(self, zone_id: str, max_squads: int) -> None:
        self.zone_id = zone_id
        self.max_squads = max_squads
        super().__init__(
            f"Гарнизон земли '{zone_id}' переполнен: максимум {max_squads} расквартированных отрядов."
        )


class SquadNotInGarrisonError(FactionError):
    """
    Попытка вывести из гарнизона отряд, которого там нет.
    """

    def __init__(self, zone_id: str, squad_id: str) -> None:
        self.zone_id = zone_id
        self.squad_id = squad_id
        super().__init__(
            f"Отряд '{squad_id}' не расквартирован в гарнизоне земли '{zone_id}'."
        )


class GarrisonLockedInBattleError(FactionError):
    """
    Состав гарнизона нельзя менять, пока за землю идет тактический бой:
    подкрепления не входят в уже начавшийся штурм, а защитники из него не выходят.
    """

    def __init__(self, zone_id: str) -> None:
        self.zone_id = zone_id
        super().__init__(
            f"Гарнизон земли '{zone_id}' связан идущим боем: состав менять нельзя."
        )


class GarrisonRotationForbiddenError(FactionError):
    """
    Ротацию гарнизона нельзя выполнить в текущей обстановке: армия стоит
    не на том гексе, связана боем или не содержит нужного отряда.
    """

    def __init__(self, zone_id: str, reason: str) -> None:
        self.zone_id = zone_id
        self.reason = reason
        super().__init__(
            f"Ротация гарнизона земли '{zone_id}' невозможна: {reason}."
        )


class MilitiaTierNotAllowedError(FactionError):
    """
    В городское ополчение попал отряд не того тира: ополчение набирается
    только из отрядов 1-2 тира.
    """

    def __init__(self, squad_name: str, tier: int, allowed_tiers: tuple[int, ...]) -> None:
        self.squad_name = squad_name
        self.tier = tier
        self.allowed_tiers = allowed_tiers
        allowed = ", ".join(str(t) for t in allowed_tiers)
        super().__init__(
            f"Отряд '{squad_name}' тира {tier} не может быть городским ополчением: разрешены тиры {allowed}."
        )


# ====================================================
# Пограничные города
# ====================================================


class BorderTownNotFoundError(FactionError):
    """
    Пограничного города с таким идентификатором у фракции нет:
    он либо не основан, либо уже стерт с лица земли.
    """

    def __init__(self, town_id: str, faction_id: str) -> None:
        self.town_id = town_id
        self.faction_id = faction_id
        super().__init__(
            f"Пограничный город '{town_id}' не найден у фракции '{faction_id}'."
        )


class BorderTownMaxLevelReachedError(FactionError):
    """
    Город уже поднят до потолка: выше четвертого уровня поселение не растет.
    """

    def __init__(self, town_name: str, max_level: int) -> None:
        self.town_name = town_name
        self.max_level = max_level
        super().__init__(
            f"Пограничный город '{town_name}' уже достиг максимального уровня {max_level}."
        )


class BorderTownMaxLandsReachedError(FactionError):
    """
    Город выкупил все положенные ему союзные земли: больше он не прокормит.
    """

    def __init__(self, town_name: str, max_lands: int) -> None:
        self.town_name = town_name
        self.max_lands = max_lands
        super().__init__(
            f"Пограничный город '{town_name}' уже заселил максимум земель: {max_lands}."
        )


class HexNotAdjacentToTownError(FactionError):
    """
    Заселять можно только гексы, вплотную примыкающие к городу: земля за
    соседним холмом городу не подчиняется.
    """

    def __init__(self, town_name: str, zone_id: str) -> None:
        self.town_name = town_name
        self.zone_id = zone_id
        super().__init__(
            f"Земля '{zone_id}' не граничит с пограничным городом '{town_name}'."
        )


class InvalidSettlementPlacementError(FactionError):
    """
    Поселение нельзя поставить на этот гекс: он занят чужой землей,
    постройкой, ориентиром Ничьей земли или вражеским войском.
    """

    def __init__(self, zone_id: str, reason: str) -> None:
        self.zone_id = zone_id
        self.reason = reason
        super().__init__(f"На гекс '{zone_id}' поселение не поставить: {reason}.")
