"""
Судьба побежденного пограничного города на уровне домена: падение уровня,
смена владельца, математика добычи и обратный отсчет операции.
"""

import pytest

from src.back.l01_domain.factions.constants import (
    BORDER_TOWN_RESOLUTION_LOOT_RATIO,
    BORDER_TOWN_RESOLUTION_TICKS,
    BorderTownResolutionType,
    MAX_BORDER_TOWN_LEVEL,
    MIN_BORDER_TOWN_LEVEL,
    OCCUPY_LEVEL_DOWNGRADE,
    PILLAGE_LEVEL_DOWNGRADE,
    ResourceType,
    border_town_resolution_loot,
)
from src.back.l01_domain.factions.models.border_town import (
    BorderTown,
    BorderTownOperation,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates

# ==================================================================
# ВСПОМОГАТЕЛЬНОЕ
# ==================================================================

CENTER = HexCoordinates.from_axial(0, 0)

INVESTMENTS = {
    ResourceType.GOLD: 1000.0,
    ResourceType.MATERIAL: 400.0,
    ResourceType.FOOD: 200.0,
}


@pytest.fixture
def town() -> BorderTown:
    settlement = BorderTown(
        faction_id="humans", name="Врата висельников", center_hex=CENTER
    )
    settlement.register_investment(INVESTMENTS)
    return settlement


def _operation(
    town: BorderTown, resolution_type: BorderTownResolutionType
) -> BorderTownOperation:
    return BorderTownOperation.start(
        town=town,
        army_id="army-1",
        conqueror_faction_id="greenskins",
        resolution_type=resolution_type,
    )


# ==================================================================
# ПАДЕНИЕ УРОВНЯ
# ==================================================================


def test_pillage_throws_the_town_two_levels_back(town: BorderTown):
    """Разграбление отбрасывает город на два уровня назад."""
    town.level = MAX_BORDER_TOWN_LEVEL

    levels_lost = town.downgrade(PILLAGE_LEVEL_DOWNGRADE)

    assert levels_lost == PILLAGE_LEVEL_DOWNGRADE
    assert town.level == MAX_BORDER_TOWN_LEVEL - PILLAGE_LEVEL_DOWNGRADE


def test_occupation_costs_the_town_a_single_level(town: BorderTown):
    """Захватчик бережет город для себя: уровень падает всего на один."""
    town.level = 3

    levels_lost = town.downgrade(OCCUPY_LEVEL_DOWNGRADE)

    assert levels_lost == OCCUPY_LEVEL_DOWNGRADE
    assert town.level == 3 - OCCUPY_LEVEL_DOWNGRADE


def test_town_never_falls_below_the_first_level(town: BorderTown):
    """
    Разоренный дотла город все равно остается городом: ниже первого
    уровня поселение не проседает.
    """
    town.level = 2

    levels_lost = town.downgrade(PILLAGE_LEVEL_DOWNGRADE)

    assert town.level == MIN_BORDER_TOWN_LEVEL
    assert levels_lost == 1, "потеряно ровно столько уровней, сколько было"


def test_downgrade_by_zero_changes_nothing(town: BorderTown):
    """Приказ уронить город на ноль уровней - приказ вхолостую."""
    town.level = 3

    assert town.downgrade(0) == 0
    assert town.level == 3


# ==================================================================
# СМЕНА ВЛАДЕЛЬЦА
# ==================================================================


def test_conquered_town_changes_its_flag(town: BorderTown):
    """Захваченный город запоминает нового хозяина."""
    town.transfer_ownership("greenskins")

    assert town.faction_id == "greenskins"


def test_ownership_transfer_keeps_the_town_intact(town: BorderTown):
    """
    Смена флага не трогает ни уровень, ни земли, ни вложения: сколько в
    город вложил прежний хозяин, столько там и остается.
    """
    land = HexCoordinates.from_axial(1, 0)
    town.claim_land(land)
    town.level = 3

    town.transfer_ownership("greenskins")

    assert town.level == 3
    assert town.claimed_hexes == [land]
    assert town.invested_resources == INVESTMENTS


# ==================================================================
# МАТЕМАТИКА ДОБЫЧИ
# ==================================================================


@pytest.mark.parametrize(
    "resolution_type,expected_ratio",
    [
        (BorderTownResolutionType.RAZE, 0.50),
        (BorderTownResolutionType.PILLAGE, 0.75),
        (BorderTownResolutionType.OCCUPY, 0.25),
    ],
)
def test_loot_is_a_share_of_everything_invested(
    town: BorderTown,
    resolution_type: BorderTownResolutionType,
    expected_ratio: float,
):
    """
    Добыча победителя - фиксированная доля от всего, что фракция вложила
    в город: чем меньше от поселения остается, тем больше уносят.
    """
    assert BORDER_TOWN_RESOLUTION_LOOT_RATIO[resolution_type] == expected_ratio

    loot = _operation(town, resolution_type).loot

    for resource, invested in INVESTMENTS.items():
        assert loot[resource] == pytest.approx(invested * expected_ratio)


def test_walking_past_the_town_brings_nothing(town: BorderTown):
    """За пропуск победитель не получает ни монеты."""
    assert border_town_resolution_loot(
        BorderTownResolutionType.IGNORE, town.invested_resources
    ) == {}


def test_loot_of_an_empty_town_is_empty():
    """С поселения, в которое ничего не вложено, и брать нечего."""
    bare_town = BorderTown(faction_id="humans", name="Пустошь", center_hex=CENTER)

    assert _operation(bare_town, BorderTownResolutionType.RAZE).loot == {}


# ==================================================================
# ХОД ОПЕРАЦИИ
# ==================================================================


@pytest.mark.parametrize(
    "resolution_type,expected_ticks",
    [
        (BorderTownResolutionType.RAZE, 3),
        (BorderTownResolutionType.PILLAGE, 2),
        (BorderTownResolutionType.OCCUPY, 2),
    ],
)
def test_operation_starts_with_its_full_countdown(
    town: BorderTown,
    resolution_type: BorderTownResolutionType,
    expected_ticks: int,
):
    """Сжечь город дольше, чем вынести его амбары: сроки заданы таблицей."""
    assert BORDER_TOWN_RESOLUTION_TICKS[resolution_type] == expected_ticks

    operation = _operation(town, resolution_type)

    assert operation.ticks_total == expected_ticks
    assert operation.ticks_remaining == expected_ticks
    assert not operation.is_finished


def test_operation_remembers_who_took_the_town_from_whom(town: BorderTown):
    """Операция помнит обе стороны: и хозяина города, и победителя."""
    operation = _operation(town, BorderTownResolutionType.OCCUPY)

    assert operation.original_faction_id == "humans"
    assert operation.conqueror_faction_id == "greenskins"
    assert operation.town_id == town.id
    assert operation.army_id == "army-1"


def test_snapshot_freezes_the_loot_at_the_start(town: BorderTown):
    """
    Добыча считается от снимка вложений: то, что фракция достроит, пока
    горит ее город, победителю уже не достанется.
    """
    operation = _operation(town, BorderTownResolutionType.RAZE)

    town.register_investment({ResourceType.GOLD: 10_000.0})

    assert operation.snapshot_invested_resources == INVESTMENTS
    assert operation.loot[ResourceType.GOLD] == pytest.approx(
        INVESTMENTS[ResourceType.GOLD] * 0.5
    )


def test_countdown_burns_one_tick_at_a_time(town: BorderTown):
    """Разрушение доходит до конца ровно за три такта, не раньше."""
    operation = _operation(town, BorderTownResolutionType.RAZE)

    assert operation.advance() is False
    assert operation.ticks_remaining == 2
    assert operation.advance() is False
    assert operation.ticks_remaining == 1
    assert operation.advance() is True
    assert operation.is_finished


def test_countdown_does_not_run_into_negatives(town: BorderTown):
    """
    Лишний такт по уже отработавшей операции не роняет счетчик ниже нуля:
    инвариант модели держится даже при повторном вызове.
    """
    operation = _operation(town, BorderTownResolutionType.PILLAGE)
    for _ in range(5):
        operation.advance()

    assert operation.ticks_remaining == 0
