"""
Иерархия доменных исключений проекта Hex & Heresy.
Все исключения предметной области наследуются от базового класса DomainError.
"""

from typing import Optional


class DomainError(Exception):
    """Базовый класс для всех исключений доменного слоя."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


# ==================================================================
# АРМИЯ И ПЕРСОНАЖИ
# ==================================================================


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


# ==================================================================
# ТАКТИЧЕСКИЙ БОЙ
# ==================================================================


class CombatError(DomainError):
    """
    Базовое исключение для ошибок тактического боя.
    """


class InvalidBattlePhaseError(CombatError):
    """
    Действие недопустимо в текущей фазе боя.
    """

    def __init__(self, current_phase: str, attempted_action: str) -> None:
        self.current_phase = current_phase
        self.attempted_action = attempted_action
        super().__init__(
            f"Действие '{attempted_action}' недопустимо в фазе боя '{current_phase}'."
        )


class CellOutOfBoundsError(CombatError):
    """
    Координаты клетки выходят за пределы сетки боя.
    """

    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        super().__init__(
            f"Клетка ({x}, {y}) выходит за пределы поля боя размером {width}x{height}."
        )


class CellOccupiedError(CombatError):
    """
    Попытка занять уже занятую клетку.
    """

    def __init__(self, x: int, y: int, occupant_id: str) -> None:
        self.x = x
        self.y = y
        self.occupant_id = occupant_id
        super().__init__(f"Клетка ({x}, {y}) уже занята отрядом '{occupant_id}'.")


class OrderNotAllowedError(CombatError):
    """
    Приказ не может быть выполнен отрядом (например, в состоянии паники).
    """

    def __init__(self, squad_id: str, reason: str) -> None:
        self.squad_id = squad_id
        self.reason = reason
        super().__init__(f"Приказ отряду '{squad_id}' отклонен: {reason}.")


class InvalidReactionError(CombatError):
    """
    Выбрана недопустимая реакция на натиск.
    """

    def __init__(self, reaction: str, reason: str) -> None:
        self.reaction = reaction
        self.reason = reason
        super().__init__(f"Реакция '{reaction}' недопустима: {reason}.")


# ==================================================================
# ФРАКЦИИ, СТРОИТЕЛЬСТВО И ЭКОНОМИКА
# ==================================================================


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


# ==================================================================
# НАЗНАЧЕНИЕ РАБОЧИХ
# ==================================================================


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


# ==================================================================
# ДИПЛОМАТИЯ
# ==================================================================


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


# ==================================================================
# ГЕОМЕТРИЯ КАРТ
# ==================================================================


class MapGeometryError(DomainError):
    """
    Базовое исключение для ошибок координат и геометрии карт.
    """


class InvalidCubeCoordinatesError(MapGeometryError):
    """
    Нарушен кубический инвариант гексагональной сетки q + r + s == 0.
    """

    def __init__(self, q: int, r: int, s: int) -> None:
        self.q = q
        self.r = r
        self.s = s
        super().__init__(
            f"Нарушен инвариант кубических координат: q({q}) + r({r}) + s({s}) = {q + r + s} != 0."
        )


class HexOutOfBoundsError(MapGeometryError):
    """
    Гекс находится за пределами допустимой глобальной карты.
    """

    def __init__(self, q: int, r: int, s: int) -> None:
        self.q = q
        self.r = r
        self.s = s
        super().__init__(f"Гекс с координатами ({q}, {r}, {s}) находится за пределами карты.")


class InvalidRadiusError(MapGeometryError):
    """
    Передан отрицательный радиус кольца или спирали.
    """

    def __init__(self, radius: int) -> None:
        self.radius = radius
        super().__init__(f"Радиус должен быть неотрицательным числом: получено {radius}.")


# ==================================================================
# ВРЕМЯ МИРА
# ==================================================================


class TimekeepingError(DomainError):
    """
    Базовое исключение для ошибок системы летоисчисления.
    """


class TimeRewindForbiddenError(TimekeepingError):
    """
    Попытка перемотать игровое время назад.
    """

    def __init__(self, ticks: int) -> None:
        self.ticks = ticks
        super().__init__(f"Нельзя перематывать игровое время назад: получено {ticks} тактов.")


# ==================================================================
# СОСТОЯНИЕ МИРА И ТРОФЕИ
# ==================================================================


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
