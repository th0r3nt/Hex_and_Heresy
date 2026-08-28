"""
Гарнизон земли: масштабирование ополчения по уровням здания, лимит
расквартированных войск, скидка на провизию и пассивное восстановление.
"""

import pytest

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions.factions import (
    GarrisonCapacityExceededError,
    GarrisonLockedInBattleError,
    MilitiaTierNotAllowedError,
    SquadNotInGarrisonError,
)
from src.back.l01_domain.factions.constants import (
    GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO,
    MAX_STATIONED_GARRISON_SQUADS,
    MILITIA_CAPACITY_BY_LEVEL,
    MILITIA_REPLENISHMENT_RATE_PER_TICK,
)
from src.back.l01_domain.factions.models.garrison import Garrison
from src.back.l01_domain.maps.models.strategic import HexCoordinates


# ==================================================================
# ВСПОМОГАТЕЛЬНОЕ
# ==================================================================


def _archetype(
    tier: int = 1,
    unit_count: int = 100,
    upkeep_food: float = 1.0,
    upkeep_gold: float = 0.5,
) -> UnitArchetype:
    return UnitArchetype(
        id=f"unit_test_tier{tier}",
        race=FactionRace.HUMANS,
        faction_id="humans",
        name=f"Отряд тира {tier}",
        tier=tier,
        default_unit_count=unit_count,
        base_stats=BaseUnitStats(max_hp=20.0),
        base_upkeep_food=upkeep_food,
        base_upkeep_gold=upkeep_gold,
    )


def _squad(**kwargs) -> Squad:
    return Squad.create_new(archetype=_archetype(**kwargs))


@pytest.fixture
def garrison() -> Garrison:
    return Garrison(
        zone_id="4,-8",
        faction_id="humans",
        hex_coordinates=HexCoordinates.from_axial(4, -8),
    )


# ==================================================================
# ВМЕСТИМОСТЬ ОПОЛЧЕНИЯ ПО УРОВНЯМ ЗДАНИЯ
# ==================================================================


@pytest.mark.parametrize("level,expected", sorted(MILITIA_CAPACITY_BY_LEVEL.items()))
def test_militia_scales_with_building_level(garrison: Garrison, level: int, expected: int):
    """Каждый уровень цитадели/ратуши задает свое число ополченцев."""
    garrison.sync_militia_capacity(level=level, recruit=_squad)

    assert len(garrison.militia_squads) == expected


def test_militia_grows_one_squad_per_upgrade(garrison: Garrison):
    """Апгрейд с 1-го на 2-й уровень открывает ровно один новый слот."""
    garrison.sync_militia_capacity(level=1, recruit=_squad)
    assert len(garrison.militia_squads) == 2

    raised, disbanded = garrison.sync_militia_capacity(level=2, recruit=_squad)

    assert len(raised) == 1
    assert disbanded == []
    assert len(garrison.militia_squads) == 3


def test_militia_is_disbanded_when_building_level_drops(garrison: Garrison):
    """Разрушенная до 1-го уровня цитадель распускает лишних ополченцев."""
    garrison.sync_militia_capacity(level=6, recruit=_squad)

    raised, disbanded = garrison.sync_militia_capacity(level=1, recruit=_squad)

    assert raised == []
    assert len(disbanded) == 4
    assert len(garrison.militia_squads) == 2


def test_repeated_sync_at_same_level_changes_nothing(garrison: Garrison):
    """Такт без апгрейдов не должен перетасовывать ополчение."""
    garrison.sync_militia_capacity(level=3, recruit=_squad)
    ids_before = [s.id for s in garrison.militia_squads]

    raised, disbanded = garrison.sync_militia_capacity(level=3, recruit=_squad)

    assert (raised, disbanded) == ([], [])
    assert [s.id for s in garrison.militia_squads] == ids_before


def test_elite_squad_cannot_be_militia(garrison: Garrison):
    """Ополчение - это горожане 1-2 тира, а не гвардия 5-го."""
    with pytest.raises(MilitiaTierNotAllowedError):
        garrison.sync_militia_capacity(level=1, recruit=lambda: _squad(tier=5))


# ==================================================================
# ЛИМИТ РАСКВАРТИРОВАННЫХ ВОЙСК
# ==================================================================


def test_stationed_squads_fill_up_to_the_limit(garrison: Garrison):
    """Земля принимает ровно MAX_STATIONED_GARRISON_SQUADS карточек."""
    for _ in range(MAX_STATIONED_GARRISON_SQUADS):
        garrison.station_squad(_squad())

    assert len(garrison.stationed_squads) == MAX_STATIONED_GARRISON_SQUADS
    assert garrison.free_stationed_slots == 0


def test_eleventh_stationed_squad_is_rejected(garrison: Garrison):
    """Одиннадцатая карточка на землю не влезает."""
    for _ in range(MAX_STATIONED_GARRISON_SQUADS):
        garrison.station_squad(_squad())

    with pytest.raises(GarrisonCapacityExceededError) as error:
        garrison.station_squad(_squad())

    assert error.value.max_squads == MAX_STATIONED_GARRISON_SQUADS
    assert len(garrison.stationed_squads) == MAX_STATIONED_GARRISON_SQUADS


def test_unstation_returns_the_squad_itself(garrison: Garrison):
    """Из гарнизона выходит тот же объект отряда, а не его копия."""
    squad = _squad()
    garrison.station_squad(squad)

    returned = garrison.unstation_squad(squad.id)

    assert returned is squad
    assert garrison.stationed_squads == []


def test_unstation_of_unknown_squad_fails(garrison: Garrison):
    with pytest.raises(SquadNotInGarrisonError):
        garrison.unstation_squad("нет-такого")


def test_militia_cannot_be_unstationed(garrison: Garrison):
    """Горожане не покидают свою землю вслед за армией."""
    garrison.sync_militia_capacity(level=1, recruit=_squad)
    militia_id = garrison.militia_squads[0].id

    with pytest.raises(SquadNotInGarrisonError):
        garrison.unstation_squad(militia_id)

    assert len(garrison.militia_squads) == 2


def test_composition_is_frozen_during_battle(garrison: Garrison):
    """Пока идет штурм, состав гарнизона менять нельзя."""
    squad = _squad()
    garrison.station_squad(squad)
    garrison.is_locked_in_battle = True

    with pytest.raises(GarrisonLockedInBattleError):
        garrison.station_squad(_squad())
    with pytest.raises(GarrisonLockedInBattleError):
        garrison.unstation_squad(squad.id)


# ==================================================================
# СОДЕРЖАНИЕ ГАРНИЗОНА
# ==================================================================


def test_food_upkeep_gets_the_garrison_discount(garrison: Garrison):
    """Провизии за стенами едят ровно на GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO меньше."""
    squad = _squad(unit_count=100, upkeep_food=1.0)
    garrison.station_squad(squad)

    expected = squad.upkeep_food * (1.0 - GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO)
    assert garrison.total_upkeep_food == pytest.approx(expected)
    assert garrison.total_upkeep_food < squad.upkeep_food


def test_gold_upkeep_is_paid_in_full(garrison: Garrison):
    """Жалование скидки не знает: за стенами платят как в поле."""
    squad = _squad(unit_count=100, upkeep_gold=0.5)
    garrison.station_squad(squad)

    assert garrison.total_upkeep_gold == pytest.approx(squad.upkeep_gold)


def test_upkeep_counts_militia_and_stationed_together(garrison: Garrison):
    """В смету идут обе половины гарнизона."""
    garrison.sync_militia_capacity(level=1, recruit=_squad)
    garrison.station_squad(_squad())

    raw_food = sum(s.upkeep_food for s in garrison.all_squads)

    assert len(garrison.all_squads) == 3
    assert garrison.total_upkeep_food == pytest.approx(
        raw_food * (1.0 - GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO)
    )


def test_all_squads_puts_militia_first(garrison: Garrison):
    """Ополчение встречает штурм первым - оно и идет первым в строю."""
    garrison.sync_militia_capacity(level=1, recruit=_squad)
    stationed = _squad()
    garrison.station_squad(stationed)

    assert garrison.all_squads[:2] == garrison.militia_squads
    assert garrison.all_squads[-1] is stationed


# ==================================================================
# ПАССИВНОЕ ВОССТАНОВЛЕНИЕ ОПОЛЧЕНИЯ
# ==================================================================


def test_militia_replenishes_a_share_of_full_strength(garrison: Garrison):
    """За такт ополчение добирает свою долю от полного штата."""
    garrison.sync_militia_capacity(level=1, recruit=lambda: _squad(unit_count=100))
    wounded = garrison.militia_squads[0]
    wounded.state.unit_count = 50

    replenished = garrison.replenish_militia_losses()

    assert replenished == [wounded.id]
    assert wounded.state.unit_count == 50 + int(100 * MILITIA_REPLENISHMENT_RATE_PER_TICK)


def test_replenishment_never_overshoots_full_strength(garrison: Garrison):
    """Недостачу в одного бойца добирают одним бойцом, а не пятнадцатью."""
    garrison.sync_militia_capacity(level=1, recruit=lambda: _squad(unit_count=100))
    almost_full = garrison.militia_squads[0]
    almost_full.state.unit_count = 99

    garrison.replenish_militia_losses()

    assert almost_full.state.unit_count == 100


def test_full_militia_is_not_reported_as_replenished(garrison: Garrison):
    """Целое ополчение не засоряет отчет такта."""
    garrison.sync_militia_capacity(level=1, recruit=_squad)

    assert garrison.replenish_militia_losses() == []


def test_wiped_militia_rebuilds_itself_from_zero(garrison: Garrison):
    """
    Гарнизон уничтожить нельзя: выбитое под ноль ополчение не пропадает,
    а отстраивается заново со следующего такта.
    """
    garrison.sync_militia_capacity(level=1, recruit=lambda: _squad(unit_count=100))
    wiped = garrison.militia_squads[0]
    wiped.state.unit_count = 0
    wiped.state.hp_first_unit = 0.0

    garrison.replenish_militia_losses()

    assert wiped in garrison.militia_squads
    assert wiped.state.unit_count == int(100 * MILITIA_REPLENISHMENT_RATE_PER_TICK)
    assert wiped.state.hp_first_unit == wiped.archetype.base_stats.max_hp


def test_tiny_militia_squad_heals_at_least_one_soldier(garrison: Garrison):
    """Крошечный отряд не должен застревать на нуле из-за округления доли."""
    garrison.sync_militia_capacity(level=1, recruit=lambda: _squad(unit_count=5))
    wounded = garrison.militia_squads[0]
    wounded.state.unit_count = 1

    garrison.replenish_militia_losses()

    assert wounded.state.unit_count == 2


def test_stationed_squads_do_not_self_heal(garrison: Garrison):
    """Регулярные войска пополняются наймом, а не сами по себе."""
    stationed = _squad(unit_count=100)
    stationed.state.unit_count = 40
    garrison.station_squad(stationed)

    assert garrison.replenish_militia_losses() == []
    assert stationed.state.unit_count == 40
