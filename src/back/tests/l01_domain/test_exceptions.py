"""
Модульные тесты для иерархии доменных исключений src/back/l01_domain/exceptions/.

Проверяет:
1. Корректность дерева наследования всех доменных ошибок относительно DomainError.
2. Сохранение и доступность структурированных контекстных атрибутов (payload) внутри объектов исключений.
3. Формирование понятных и информативных строковых описаний ошибок для логов и интерфейса.
"""

import pytest

from src.back.l01_domain.exceptions.army import (
    ArmyError,
    CommanderAlreadyAssignedError,
    HeroAlreadyWoundedError,
    HeroLevelTooLowError,
    InvalidEquipmentSlotError,
    NegativeExperienceError,
    SquadDepletedError,
)
from src.back.l01_domain.exceptions.base import DomainError
from src.back.l01_domain.exceptions.combat import (
    CellOccupiedError,
    CellOutOfBoundsError,
    CombatError,
    InvalidBattlePhaseError,
    InvalidReactionError,
    OrderNotAllowedError,
)
from src.back.l01_domain.exceptions.diplomacy import (
    AmbassadorUnavailableError,
    DiplomacyError,
    DiplomaticRelationNotFoundError,
    PactForbiddenDuringWarError,
    WarAllianceWithEnemyForbiddenError,
)
from src.back.l01_domain.exceptions.factions import (
    BuildingMaxLevelReachedError,
    BuildingSlotsExhaustedError,
    FactionError,
    InsufficientResourcesError,
    NegativeResourceAmountError,
    ZoneNotControlledError,
)
from src.back.l01_domain.exceptions.maps import (
    HexOutOfBoundsError,
    InvalidCubeCoordinatesError,
    InvalidRadiusError,
    MapGeometryError,
)
from src.back.l01_domain.exceptions.timekeeping import TimeRewindForbiddenError, TimekeepingError
from src.back.l01_domain.exceptions.world import BattlefieldDepletedError, WorldStateError


class TestExceptionsHierarchy:
    """Проверка корректности дерева наследования всех доменных исключений."""

    @pytest.mark.parametrize(
        ("exception_cls", "parent_cls"),
        [
            # Базовые поддоменные категории
            (ArmyError, DomainError),
            (CombatError, DomainError),
            (FactionError, DomainError),
            (DiplomacyError, FactionError),
            (MapGeometryError, DomainError),
            (TimekeepingError, DomainError),
            (WorldStateError, DomainError),
            # Армия и персонажи
            (SquadDepletedError, ArmyError),
            (InvalidEquipmentSlotError, ArmyError),
            (HeroLevelTooLowError, ArmyError),
            (HeroAlreadyWoundedError, ArmyError),
            (NegativeExperienceError, ArmyError),
            (CommanderAlreadyAssignedError, ArmyError),
            # Тактический бой
            (InvalidBattlePhaseError, CombatError),
            (CellOutOfBoundsError, CombatError),
            (CellOccupiedError, CombatError),
            (OrderNotAllowedError, CombatError),
            (InvalidReactionError, CombatError),
            # Фракции, строительство и экономика
            (InsufficientResourcesError, FactionError),
            (NegativeResourceAmountError, FactionError),
            (BuildingMaxLevelReachedError, FactionError),
            (BuildingSlotsExhaustedError, FactionError),
            (ZoneNotControlledError, FactionError),
            # Дипломатия
            (PactForbiddenDuringWarError, DiplomacyError),
            (WarAllianceWithEnemyForbiddenError, DiplomacyError),
            (DiplomaticRelationNotFoundError, DiplomacyError),
            (AmbassadorUnavailableError, DiplomacyError),
            # Геометрия карт
            (InvalidCubeCoordinatesError, MapGeometryError),
            (HexOutOfBoundsError, MapGeometryError),
            (InvalidRadiusError, MapGeometryError),
            # Время мира
            (TimeRewindForbiddenError, TimekeepingError),
            # Состояние мира и трофеи
            (BattlefieldDepletedError, WorldStateError),
        ],
    )
    def test_subclassing_relationship(
        self, exception_cls: type[DomainError], parent_cls: type[DomainError]
    ) -> None:
        """Проверяет прямое наследование от родительской категории и базового класса DomainError."""
        assert issubclass(exception_cls, parent_cls)
        assert issubclass(exception_cls, DomainError)


class TestArmyExceptions:
    """Тестирование исключений поддомена армии и персонажей."""

    def test_squad_depleted_error_payload(self) -> None:
        """Проверяет сохранение идентификатора отряда и текст сообщения об уничтожении."""
        error = SquadDepletedError(squad_id="squad_123")
        assert error.squad_id == "squad_123"
        assert "squad_123" in str(error)
        assert "полностью уничтожен" in str(error)

    def test_invalid_equipment_slot_error_payload(self) -> None:
        """Проверяет корректность атрибутов слотов и форматирование текста ошибки несовместимости."""
        error = InvalidEquipmentSlotError(
            item_id="sword_01", expected_slot="armor", actual_slot="weapon"
        )
        assert error.item_id == "sword_01"
        assert error.expected_slot == "armor"
        assert error.actual_slot == "weapon"
        assert "sword_01" in str(error)
        assert "weapon" in str(error)
        assert "armor" in str(error)

    def test_hero_level_too_low_error_with_perk_id(self) -> None:
        """Проверяет атрибуты уровней и текст ошибки при указании конкретного идентификатора перка."""
        error = HeroLevelTooLowError(
            current_level=2, required_level=5, perk_id="perk_iron_gut"
        )
        assert error.current_level == 2
        assert error.required_level == 5
        assert error.perk_id == "perk_iron_gut"
        assert "2" in str(error)
        assert "5" in str(error)
        assert "perk_iron_gut" in str(error)

    def test_hero_level_too_low_error_without_perk_id(self) -> None:
        """Проверяет текст ошибки при отсутствии переданного идентификатора перка."""
        error = HeroLevelTooLowError(current_level=1, required_level=3)
        assert error.perk_id is None
        assert "уровень 3" in str(error)

    def test_hero_already_wounded_error_payload(self) -> None:
        """Проверяет сохранение идентификатора героя и сообщение о повторном ранении."""
        error = HeroAlreadyWoundedError(hero_id="hero_grom")
        assert error.hero_id == "hero_grom"
        assert "hero_grom" in str(error)
        assert "тяжелого ранения" in str(error)

    def test_negative_experience_error_payload(self) -> None:
        """Проверяет сохранение недопустимого значения опыта и текст ошибки."""
        error = NegativeExperienceError(amount=-100)
        assert error.amount == -100
        assert "-100" in str(error)

    def test_commander_already_assigned_error_payload(self) -> None:
        """Проверяет фиксацию текущей армии и идентификатора полководца."""
        error = CommanderAlreadyAssignedError(
            commander_id="cmd_01", current_army_id="army_north"
        )
        assert error.commander_id == "cmd_01"
        assert error.current_army_id == "army_north"
        assert "cmd_01" in str(error)
        assert "army_north" in str(error)


class TestCombatExceptions:
    """Тестирование исключений поддомена тактического боя."""

    def test_invalid_battle_phase_error_payload(self) -> None:
        """Проверяет фиксацию текущей фазы боя и недопустимого действия."""
        error = InvalidBattlePhaseError(current_phase="deployment", attempted_action="attack")
        assert error.current_phase == "deployment"
        assert error.attempted_action == "attack"
        assert "deployment" in str(error)
        assert "attack" in str(error)

    def test_cell_out_of_bounds_error_payload(self) -> None:
        """Проверяет фиксацию координат клетки и габаритов поля боя."""
        error = CellOutOfBoundsError(x=20, y=5, width=20, height=20)
        assert error.x == 20
        assert error.y == 5
        assert error.width == 20
        assert error.height == 20
        assert "(20, 5)" in str(error)
        assert "20x20" in str(error)

    def test_cell_occupied_error_payload(self) -> None:
        """Проверяет фиксацию координат клетки и идентификатора отряда, занимающего клетку."""
        error = CellOccupiedError(x=3, y=4, occupant_id="squad_enemy")
        assert error.x == 3
        assert error.y == 4
        assert error.occupant_id == "squad_enemy"
        assert "(3, 4)" in str(error)
        assert "squad_enemy" in str(error)

    def test_order_not_allowed_error_payload(self) -> None:
        """Проверяет фиксацию причины отклонения приказа отряду."""
        error = OrderNotAllowedError(
            squad_id="squad_archers", reason="отряд находится в панике"
        )
        assert error.squad_id == "squad_archers"
        assert error.reason == "отряд находится в панике"
        assert "squad_archers" in str(error)
        assert "отряд находится в панике" in str(error)

    def test_invalid_reaction_error_payload(self) -> None:
        """Проверяет фиксацию типа реакции и причины ее недопустимости."""
        error = InvalidReactionError(reaction="accept_charge", reason="отряд не имеет копий")
        assert error.reaction == "accept_charge"
        assert error.reason == "отряд не имеет копий"
        assert "accept_charge" in str(error)
        assert "отряд не имеет копий" in str(error)


class TestFactionExceptions:
    """Тестирование исключений поддомена фракций, экономики и строительства."""

    def test_insufficient_resources_error_with_faction(self) -> None:
        """Проверяет атрибуты дефицита ресурсов с указанием идентификатора фракции."""
        error = InsufficientResourcesError(
            resource="gold", required=100.0, available=40.0, faction_id="faction_humans"
        )
        assert error.resource == "gold"
        assert error.required == 100.0
        assert error.available == 40.0
        assert error.faction_id == "faction_humans"
        assert "gold" in str(error)
        assert "100.0" in str(error)
        assert "40.0" in str(error)
        assert "faction_humans" in str(error)

    def test_insufficient_resources_error_without_faction(self) -> None:
        """Проверяет текст ошибки нехватки ресурсов без указания фракции."""
        error = InsufficientResourcesError(resource="material", required=50.0, available=10.0)
        assert error.faction_id is None
        assert "material" in str(error)

    def test_negative_resource_amount_error_payload(self) -> None:
        """Проверяет фиксацию отрицательного значения ресурса и наименования операции."""
        error = NegativeResourceAmountError(amount=-25.0, operation="spend")
        assert error.amount == -25.0
        assert error.operation == "spend"
        assert "-25.0" in str(error)
        assert "spend" in str(error)

    def test_building_max_level_reached_error_payload(self) -> None:
        """Проверяет фиксацию названия здания и предельного уровня улучшения."""
        error = BuildingMaxLevelReachedError(building_name="Цитадель", max_level=6)
        assert error.building_name == "Цитадель"
        assert error.max_level == 6
        assert "Цитадель" in str(error)
        assert "6" in str(error)

    def test_building_slots_exhausted_error_payload(self) -> None:
        """Проверяет фиксацию зоны и лимита строительных слотов."""
        error = BuildingSlotsExhaustedError(zone_id="zone_allied_01", max_slots=3)
        assert error.zone_id == "zone_allied_01"
        assert error.max_slots == 3
        assert "zone_allied_01" in str(error)
        assert "3" in str(error)

    def test_zone_not_controlled_error_payload(self) -> None:
        """Проверяет фиксацию зоны и фракции при попытке несанкционированного контроля."""
        error = ZoneNotControlledError(faction_id="faction_orcs", zone_id="zone_neutral_99")
        assert error.faction_id == "faction_orcs"
        assert error.zone_id == "zone_neutral_99"
        assert "faction_orcs" in str(error)
        assert "zone_neutral_99" in str(error)


class TestDiplomacyExceptions:
    """Тестирование исключений поддомена дипломатии."""

    def test_pact_forbidden_during_war_error_payload(self) -> None:
        """Проверяет фиксацию типа соглашения и идентификаторов воюющих сторон."""
        error = PactForbiddenDuringWarError(
            pact_name="trade", faction_a_id="humans", faction_b_id="orcs"
        )
        assert error.pact_name == "trade"
        assert error.faction_a_id == "humans"
        assert error.faction_b_id == "orcs"
        assert "trade" in str(error)
        assert "humans" in str(error)
        assert "orcs" in str(error)

    def test_war_alliance_with_enemy_forbidden_error_payload(self) -> None:
        """Проверяет сообщение об ошибке при попытке заключить союз с текущим врагом."""
        error = WarAllianceWithEnemyForbiddenError(faction_a_id="humans", faction_b_id="orcs")
        assert error.faction_a_id == "humans"
        assert error.faction_b_id == "orcs"
        assert "orcs" in str(error)
        assert "военный союз" in str(error)

    def test_diplomatic_relation_not_found_error_payload(self) -> None:
        """Проверяет фиксацию отсутствующих дипломатических отношений между фракциями."""
        error = DiplomaticRelationNotFoundError(faction_a_id="elfs", faction_b_id="baronies")
        assert error.faction_a_id == "elfs"
        assert error.faction_b_id == "baronies"
        assert "elfs" in str(error)
        assert "baronies" in str(error)

    def test_ambassador_unavailable_error_payload(self) -> None:
        """Проверяет фиксацию идентификатора посла и его текущего недоступного статуса."""
        error = AmbassadorUnavailableError(ambassador_id="amb_valter", status="executed")
        assert error.ambassador_id == "amb_valter"
        assert error.status == "executed"
        assert "amb_valter" in str(error)
        assert "executed" in str(error)


class TestMapGeometryExceptions:
    """Тестирование исключений геометрии карт и координат."""

    def test_invalid_cube_coordinates_error_payload(self) -> None:
        """Проверяет расчет суммы координат и форматирование текста при нарушении инварианта."""
        error = InvalidCubeCoordinatesError(q=2, r=-1, s=1)
        assert error.q == 2
        assert error.r == -1
        assert error.s == 1
        assert "q(2) + r(-1) + s(1)" in str(error)
        assert "= 2 != 0" in str(error)

    def test_hex_out_of_bounds_error_payload(self) -> None:
        """Проверяет фиксацию координат гекса, вышедшего за границы глобальной карты."""
        error = HexOutOfBoundsError(q=100, r=-50, s=-50)
        assert error.q == 100
        assert error.r == -50
        assert error.s == -50
        assert "(100, -50, -50)" in str(error)

    def test_invalid_radius_error_payload(self) -> None:
        """Проверяет фиксацию отрицательного значения радиуса."""
        error = InvalidRadiusError(radius=-3)
        assert error.radius == -3
        assert "-3" in str(error)


class TestTimekeepingExceptions:
    """Тестирование исключений системы времени."""

    def test_time_rewind_forbidden_error_payload(self) -> None:
        """Проверяет фиксацию отрицательного числа тактов перемотки времени."""
        error = TimeRewindForbiddenError(ticks=-10)
        assert error.ticks == -10
        assert "-10" in str(error)
        assert "Нельзя перематывать" in str(error)


class TestWorldStateExceptions:
    """Тестирование исключений состояния мира и полей брани."""

    def test_battlefield_depleted_error_payload(self) -> None:
        """Проверяет фиксацию идентификатора истощенного поля брани."""
        error = BattlefieldDepletedError(site_id="site_blood_01")
        assert error.site_id == "site_blood_01"
        assert "site_blood_01" in str(error)
        assert "истощено или истлело" in str(error)
