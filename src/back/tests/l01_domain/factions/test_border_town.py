"""
Пограничный город: инварианты уровня, лимит и смежность выкупаемых земель,
строительные слоты и вклад города в налогооблагаемую базу фракции.
"""

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions.factions import (
    BorderTownMaxLandsReachedError,
    BorderTownMaxLevelReachedError,
    HexNotAdjacentToTownError,
)
from src.back.l01_domain.factions.constants import (
    BASE_TAX_BORDER_TOWN_PER_LEVEL,
    BASE_TAX_HQ_PER_LEVEL,
    BASE_TAX_ZONE_PER_LEVEL,
    BORDER_TOWN_FOUNDATION_COST,
    MAX_BORDER_TOWN_ALLIED_LANDS,
    MAX_BORDER_TOWN_LEVEL,
    MIN_BORDER_TOWN_LEVEL,
    ResourceType,
)
from src.back.l01_domain.factions.models.border_town import BorderTown
from src.back.l01_domain.factions.models.buildings import Headquarters, RegionalHall
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    hex_neighbors,
    hex_zone_id,
)


# ==================================================================
# ВСПОМОГАТЕЛЬНОЕ
# ==================================================================

CENTER = HexCoordinates.from_axial(0, 0)


@pytest.fixture
def town() -> BorderTown:
    return BorderTown(faction_id="humans", name="Врата висельников", center_hex=CENTER)


@pytest.fixture
def faction() -> Faction:
    return Faction(
        id="humans",
        race=FactionRace.HUMANS,
        name="Священная Империя",
        lord=Lord(faction_id="humans", name="Валленштейн", title="Лорд-командующий"),
        headquarters=Headquarters(faction_id="humans", name="Цитадель"),
    )


# ==================================================================
# УРОВНИ ГОРОДА
# ==================================================================


def test_new_town_starts_at_first_level(town: BorderTown):
    """Основанный город встает на первом уровне: расти ему еще некуда."""
    assert town.level == MIN_BORDER_TOWN_LEVEL


def test_town_grows_up_to_the_fourth_level(town: BorderTown):
    """Город поднимается ровно до четвертого уровня."""
    for expected_level in range(MIN_BORDER_TOWN_LEVEL + 1, MAX_BORDER_TOWN_LEVEL + 1):
        town.upgrade()
        assert town.level == expected_level


def test_fifth_upgrade_is_refused(town: BorderTown):
    """Пятого уровня у поселения не бывает - потолок жесткий."""
    for _ in range(MAX_BORDER_TOWN_LEVEL - MIN_BORDER_TOWN_LEVEL):
        town.upgrade()

    with pytest.raises(BorderTownMaxLevelReachedError):
        town.upgrade()

    assert town.level == MAX_BORDER_TOWN_LEVEL


def test_upgrade_check_does_not_touch_the_town(town: BorderTown):
    """
    Проверка перед списанием казны ничего не меняет: иначе город рос бы
    от одного намерения игрока.
    """
    town.assert_can_upgrade()

    assert town.level == MIN_BORDER_TOWN_LEVEL


@pytest.mark.parametrize(
    "level,expected_slots",
    [(1, 2), (2, 3), (3, 4), (4, 5)],
)
def test_each_level_opens_one_building_slot(
    town: BorderTown, level: int, expected_slots: int
):
    """На первом уровне в городе 2 слота, на четвертом - 5."""
    town.level = level

    assert town.building_slots == expected_slots


# ==================================================================
# ЗАСЕЛЕНИЕ СОЮЗНЫХ ЗЕМЕЛЬ
# ==================================================================


def test_town_claims_up_to_four_adjacent_hexes(town: BorderTown):
    """Город заселяет ровно четыре смежных гекса."""
    for coord in hex_neighbors(CENTER)[:MAX_BORDER_TOWN_ALLIED_LANDS]:
        town.claim_land(coord)

    assert len(town.claimed_hexes) == MAX_BORDER_TOWN_ALLIED_LANDS
    assert town.free_land_slots == 0


def test_fifth_land_is_refused_even_if_adjacent(town: BorderTown):
    """
    Пятый гекс не заселить, даже если он и правда граничит с городом:
    больше поселение не прокормит.
    """
    neighbors = hex_neighbors(CENTER)
    for coord in neighbors[:MAX_BORDER_TOWN_ALLIED_LANDS]:
        town.claim_land(coord)

    with pytest.raises(BorderTownMaxLandsReachedError):
        town.claim_land(neighbors[MAX_BORDER_TOWN_ALLIED_LANDS])

    assert len(town.claimed_hexes) == MAX_BORDER_TOWN_ALLIED_LANDS


def test_distant_hex_is_not_adjacent_to_the_town(town: BorderTown):
    """Земля через гекс от города ему не подчиняется."""
    far_hex = HexCoordinates.from_axial(2, 0)

    with pytest.raises(HexNotAdjacentToTownError):
        town.claim_land(far_hex)

    assert town.claimed_hexes == []


def test_own_hex_is_not_claimable_land(town: BorderTown):
    """Гекс самого города - не союзная земля: он уже занят поселением."""
    with pytest.raises(HexNotAdjacentToTownError):
        town.claim_land(CENTER)


def test_repeated_claim_changes_nothing(town: BorderTown):
    """Повторный выкуп той же земли - приказ вхолостую, а не ошибка."""
    coord = hex_neighbors(CENTER)[0]
    town.claim_land(coord)
    town.claim_land(coord)

    assert town.claimed_hexes == [coord]


def test_lost_land_leaves_the_town(town: BorderTown):
    """Отбитая врагом земля выпадает из владений города."""
    coord = hex_neighbors(CENTER)[0]
    town.claim_land(coord)

    town.release_zone(hex_zone_id(coord))

    assert town.claimed_hexes == []
    assert town.free_land_slots == MAX_BORDER_TOWN_ALLIED_LANDS


# ==================================================================
# УЧЕТ ВЛОЖЕНИЙ
# ==================================================================


def test_investments_accumulate_across_purchases(town: BorderTown):
    """
    Траты на город копятся: от этой суммы захватчик отсчитывает свою добычу.
    """
    town.register_investment(BORDER_TOWN_FOUNDATION_COST)
    town.register_investment({ResourceType.GOLD: 100.0})

    expected_gold = BORDER_TOWN_FOUNDATION_COST[ResourceType.GOLD] + 100.0
    assert town.invested_resources[ResourceType.GOLD] == expected_gold
    assert (
        town.invested_resources[ResourceType.MATERIAL]
        == BORDER_TOWN_FOUNDATION_COST[ResourceType.MATERIAL]
    )


# ==================================================================
# ГОРОДА В СОСТАВЕ ФРАКЦИИ
# ==================================================================


def test_town_pays_poll_tax_on_top_of_the_citadel(faction: Faction, town: BorderTown):
    """Город платит подушный сбор наравне с цитаделью."""
    base_without_town = faction.taxable_base_gold
    town.level = 3
    faction.add_border_town(town)

    expected = base_without_town + 3 * BASE_TAX_BORDER_TOWN_PER_LEVEL
    assert faction.taxable_base_gold == expected


def test_claimed_land_hall_is_taxed_once(faction: Faction, town: BorderTown):
    """
    Ратуша выкупленной земли считается один раз - как обычная союзная
    ратуша, а не дважды за счет города.
    """
    coord = hex_neighbors(CENTER)[0]
    town.claim_land(coord)
    faction.add_border_town(town)
    faction.gain_zone(hex_zone_id(coord))
    faction.add_regional_hall(
        RegionalHall(faction_id=faction.id, zone_id=hex_zone_id(coord), name="Ратуша")
    )

    expected = (
        faction.headquarters.level * BASE_TAX_HQ_PER_LEVEL
        + BASE_TAX_BORDER_TOWN_PER_LEVEL
        + BASE_TAX_ZONE_PER_LEVEL
    )
    assert faction.taxable_base_gold == expected


def test_losing_the_town_hex_wipes_the_settlement(faction: Faction, town: BorderTown):
    """
    Взятая врагом земля города стирает поселение целиком: вместе с ним
    фракция теряет и все выкупленные им земли с их ратушами.
    """
    land = hex_neighbors(CENTER)[0]
    land_zone_id = hex_zone_id(land)

    town.claim_land(land)
    faction.add_border_town(town)
    faction.gain_zone(town.zone_id)
    faction.gain_zone(land_zone_id)
    faction.add_regional_hall(
        RegionalHall(faction_id=faction.id, zone_id=land_zone_id, name="Ратуша")
    )

    faction.lose_zone(town.zone_id)

    assert faction.border_towns == []
    assert faction.controlled_zone_ids == []
    assert faction.regional_halls == []


def test_losing_a_claimed_land_leaves_the_town_standing(
    faction: Faction, town: BorderTown
):
    """Потеря одной земли не сносит сам город - он лишь беднеет."""
    land = hex_neighbors(CENTER)[0]
    town.claim_land(land)
    faction.add_border_town(town)
    faction.gain_zone(town.zone_id)
    faction.gain_zone(hex_zone_id(land))

    faction.lose_zone(hex_zone_id(land))

    assert faction.get_border_town(town.id) is town
    assert town.claimed_hexes == []
    assert faction.controlled_zone_ids == [town.zone_id]
