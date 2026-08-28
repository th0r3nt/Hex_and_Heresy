"""
Пограничные города на глобальном такте: основание и выкуп земель бьют по
казне, город поднимает собственный гарнизон и платит налоги наравне со
столицей.
"""

import pytest

from src.back.l01_domain.army.constants import StrategicMovementPace
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.exceptions.factions import (
    BorderTownMaxLandsReachedError,
    BorderTownNotFoundError,
    FactionNotFoundError,
    HexNotAdjacentToTownError,
    InsufficientResourcesError,
    InvalidSettlementPlacementError,
)
from src.back.l01_domain.factions.constants import (
    BASE_TAX_BORDER_TOWN_PER_LEVEL,
    BORDER_TOWN_FOUNDATION_COST,
    BORDER_TOWN_LAND_CLAIM_COST,
    MAX_BORDER_TOWN_ALLIED_LANDS,
    ResourceType,
    border_town_upgrade_cost,
    militia_capacity_for_level,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    hex_neighbors,
    hex_zone_id,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.settlements.facade import SettlementsFacade
from src.back.l02_services.turns.strategic.economy import StrategicEconomyService
from src.back.l02_services.turns.strategic.garrison import GarrisonService
from src.back.utils.event.registry import GameEvents

# Гекс в Ничьей земле, далекий от любой цитадели
FRONTIER = HexCoordinates.from_axial(0, 0)


# ==================================================================
# ВСПОМОГАТЕЛЬНОЕ
# ==================================================================


@pytest.fixture
def world(human_faction: Faction) -> WorldState:
    """Мир с одной богатой фракцией и одним свободным гексом под город."""
    human_faction.resources[ResourceType.GOLD] = 5000.0
    human_faction.resources[ResourceType.MATERIAL] = 5000.0
    human_faction.resources[ResourceType.FOOD] = 5000.0
    human_faction.capital_hex = HexCoordinates.from_axial(4, -8)

    state = WorldState()
    state.add_faction(human_faction)
    state.neutral_hexes.append(FRONTIER)
    return state


@pytest.fixture
def service(fake_bus) -> SettlementsFacade:
    return SettlementsFacade(event_bus=fake_bus)


# ==================================================================
# ОСНОВАНИЕ ГОРОДА
# ==================================================================


async def test_founding_charges_the_treasury_and_takes_the_hex(
    service: SettlementsFacade, world: WorldState, human_faction: Faction, fake_bus
):
    """
    Основание списывает полную стоимость, забирает гекс из Ничьей земли
    и записывает трату в вложения города.
    """
    gold_before = human_faction.resources[ResourceType.GOLD]

    town = await service.found_border_town(
        world_state=world,
        faction_id=human_faction.id,
        target_hex=FRONTIER,
        name="Врата висельников",
    )

    assert town.level == 1
    assert town.building_slots == 2
    assert human_faction.resources[ResourceType.GOLD] == (
        gold_before - BORDER_TOWN_FOUNDATION_COST[ResourceType.GOLD]
    )
    assert town.invested_resources == dict(BORDER_TOWN_FOUNDATION_COST)

    assert human_faction.border_towns == [town]
    assert town.zone_id in human_faction.controlled_zone_ids
    assert FRONTIER not in world.neutral_hexes

    assert any(
        name == GameEvents.Economy.BORDER_TOWN_FOUNDED for name, _ in fake_bus.events
    )


async def test_empty_treasury_leaves_the_map_untouched(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """
    Не хватило ресурсов - города нет и гекс остается нейтральным:
    неудавшийся приказ не должен оставлять следов.
    """
    human_faction.resources[ResourceType.MATERIAL] = 0.0

    with pytest.raises(InsufficientResourcesError):
        await service.found_border_town(
            world_state=world,
            faction_id=human_faction.id,
            target_hex=FRONTIER,
            name="Врата висельников",
        )

    assert human_faction.border_towns == []
    assert FRONTIER in world.neutral_hexes


async def test_second_town_on_the_same_hex_is_refused(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """Гекс, занятый своим же городом, под второе поселение не годится."""
    await service.found_border_town(
        world_state=world,
        faction_id=human_faction.id,
        target_hex=FRONTIER,
        name="Врата висельников",
    )

    with pytest.raises(InvalidSettlementPlacementError):
        await service.found_border_town(
            world_state=world,
            faction_id=human_faction.id,
            target_hex=FRONTIER,
            name="Второй город",
        )

    assert len(human_faction.border_towns) == 1


async def test_town_is_not_founded_under_a_foreign_army(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """Под носом у чужого войска обоз с поселенцами не разгрузить."""
    world.add_army(
        StrategicArmy(
            faction_id="greenskins",
            name="Орда Ржавых Клыков",
            current_hex=FRONTIER,
            pace=StrategicMovementPace.MARCH,
        )
    )

    with pytest.raises(InvalidSettlementPlacementError):
        await service.found_border_town(
            world_state=world,
            faction_id=human_faction.id,
            target_hex=FRONTIER,
            name="Врата висельников",
        )


async def test_unknown_faction_cannot_found_a_town(
    service: SettlementsFacade, world: WorldState
):
    """Приказ от несуществующей фракции - доменная ошибка, а не молчание."""
    with pytest.raises(FactionNotFoundError):
        await service.found_border_town(
            world_state=world,
            faction_id="нет-такой",
            target_hex=FRONTIER,
            name="Город-призрак",
        )


# ==================================================================
# РОСТ ГОРОДА
# ==================================================================


async def test_upgrade_charges_the_level_price(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """Апгрейд списывает цену целевого уровня и открывает новый слот."""
    town = await service.found_border_town(
        world_state=world,
        faction_id=human_faction.id,
        target_hex=FRONTIER,
        name="Врата висельников",
    )
    gold_before = human_faction.resources[ResourceType.GOLD]

    await service.upgrade_border_town(
        world_state=world, faction_id=human_faction.id, town_id=town.id
    )

    cost = border_town_upgrade_cost(2)
    assert town.level == 2
    assert town.building_slots == 3
    assert human_faction.resources[ResourceType.GOLD] == (
        gold_before - cost[ResourceType.GOLD]
    )


async def test_upgrade_of_unknown_town_is_refused(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """Несуществующий город улучшить нельзя."""
    with pytest.raises(BorderTownNotFoundError):
        await service.upgrade_border_town(
            world_state=world, faction_id=human_faction.id, town_id="нет-такого"
        )


async def test_failed_upgrade_keeps_the_gold(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """
    Без денег на апгрейд город остается прежним, а казна - нетронутой.
    """
    town = await service.found_border_town(
        world_state=world,
        faction_id=human_faction.id,
        target_hex=FRONTIER,
        name="Врата висельников",
    )
    human_faction.resources[ResourceType.GOLD] = 0.0

    with pytest.raises(InsufficientResourcesError):
        await service.upgrade_border_town(
            world_state=world, faction_id=human_faction.id, town_id=town.id
        )

    assert town.level == 1
    assert human_faction.resources[ResourceType.GOLD] == 0.0


# ==================================================================
# ЗАСЕЛЕНИЕ СМЕЖНЫХ ЗЕМЕЛЬ
# ==================================================================


async def test_claimed_land_gets_a_hall_and_joins_the_faction(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """
    Выкупленная земля переходит под контроль фракции вместе с ратушей -
    с этого момента она дает слот и платит налог.
    """
    town = await service.found_border_town(
        world_state=world,
        faction_id=human_faction.id,
        target_hex=FRONTIER,
        name="Врата висельников",
    )
    land = hex_neighbors(FRONTIER)[0]
    gold_before = human_faction.resources[ResourceType.GOLD]

    await service.claim_border_land(
        world_state=world,
        faction_id=human_faction.id,
        town_id=town.id,
        target_hex=land,
    )

    zone_id = hex_zone_id(land)
    assert town.claimed_hexes == [land]
    assert zone_id in human_faction.controlled_zone_ids
    assert human_faction.get_regional_hall(zone_id) is not None
    assert human_faction.resources[ResourceType.GOLD] == (
        gold_before - BORDER_TOWN_LAND_CLAIM_COST[ResourceType.GOLD]
    )


async def test_only_adjacent_land_is_for_sale(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """Землю через гекс от города не выкупить, а казна остается целой."""
    town = await service.found_border_town(
        world_state=world,
        faction_id=human_faction.id,
        target_hex=FRONTIER,
        name="Врата висельников",
    )
    gold_before = human_faction.resources[ResourceType.GOLD]

    with pytest.raises(HexNotAdjacentToTownError):
        await service.claim_border_land(
            world_state=world,
            faction_id=human_faction.id,
            town_id=town.id,
            target_hex=HexCoordinates.from_axial(3, 0),
        )

    assert town.claimed_hexes == []
    assert human_faction.resources[ResourceType.GOLD] == gold_before


async def test_town_stops_at_four_lands(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """Пятую землю город не выкупит, сколько бы золота ни лежало в казне."""
    town = await service.found_border_town(
        world_state=world,
        faction_id=human_faction.id,
        target_hex=FRONTIER,
        name="Врата висельников",
    )
    neighbors = hex_neighbors(FRONTIER)

    for coord in neighbors[:MAX_BORDER_TOWN_ALLIED_LANDS]:
        await service.claim_border_land(
            world_state=world,
            faction_id=human_faction.id,
            town_id=town.id,
            target_hex=coord,
        )

    with pytest.raises(BorderTownMaxLandsReachedError):
        await service.claim_border_land(
            world_state=world,
            faction_id=human_faction.id,
            town_id=town.id,
            target_hex=neighbors[MAX_BORDER_TOWN_ALLIED_LANDS],
        )

    assert len(town.claimed_hexes) == MAX_BORDER_TOWN_ALLIED_LANDS
    assert len(human_faction.regional_halls) == MAX_BORDER_TOWN_ALLIED_LANDS


# ==================================================================
# ГОРОД В ЭКОНОМИКЕ И ОБОРОНЕ ТАКТА
# ==================================================================


async def test_town_income_reaches_the_treasury_on_the_next_tick(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """
    Подушный сбор с города приходит в казну обычным экономическим шагом,
    без единой правки в самом сервисе экономики.
    """
    base_without_town = human_faction.taxable_base_gold
    await service.found_border_town(
        world_state=world,
        faction_id=human_faction.id,
        target_hex=FRONTIER,
        name="Врата висельников",
    )

    reports = await StrategicEconomyService().process_factions_economy(world)

    expected_tax = (
        base_without_town + BASE_TAX_BORDER_TOWN_PER_LEVEL
    ) * human_faction.tax_rate
    assert reports[human_faction.id].tax_income_gold == expected_tax


async def test_town_and_its_lands_raise_their_own_garrisons(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """
    Город - такой же административный центр, как цитадель: на ближайшем
    такте он и его земли поднимают собственное ополчение.
    """
    town = await service.found_border_town(
        world_state=world,
        faction_id=human_faction.id,
        target_hex=FRONTIER,
        name="Врата висельников",
    )
    land = hex_neighbors(FRONTIER)[0]
    await service.claim_border_land(
        world_state=world,
        faction_id=human_faction.id,
        town_id=town.id,
        target_hex=land,
    )

    await GarrisonService().process_garrisons(world)

    town_garrison = world.get_garrison(town.zone_id)
    land_garrison = world.get_garrison(hex_zone_id(land))

    assert town_garrison is not None
    assert land_garrison is not None
    assert len(town_garrison.militia_squads) == militia_capacity_for_level(town.level)


async def test_upgraded_town_holds_a_bigger_militia(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """Апгрейд города открывает слот ополчения - земля поднимает еще отряд."""
    town = await service.found_border_town(
        world_state=world,
        faction_id=human_faction.id,
        target_hex=FRONTIER,
        name="Врата висельников",
    )
    garrisons = GarrisonService()
    await garrisons.process_garrisons(world)

    await service.upgrade_border_town(
        world_state=world, faction_id=human_faction.id, town_id=town.id
    )
    await garrisons.process_garrisons(world)

    garrison = world.get_garrison(town.zone_id)
    assert len(garrison.militia_squads) == militia_capacity_for_level(2)


async def test_lost_town_hex_takes_its_garrisons_off_the_map(
    service: SettlementsFacade, world: WorldState, human_faction: Faction
):
    """
    Взятый врагом город исчезает вместе со своими землями, а такт снимает
    с карты их осиротевшие гарнизоны.
    """
    town = await service.found_border_town(
        world_state=world,
        faction_id=human_faction.id,
        target_hex=FRONTIER,
        name="Врата висельников",
    )
    land = hex_neighbors(FRONTIER)[0]
    await service.claim_border_land(
        world_state=world,
        faction_id=human_faction.id,
        town_id=town.id,
        target_hex=land,
    )

    garrisons = GarrisonService()
    await garrisons.process_garrisons(world)

    human_faction.lose_zone(town.zone_id)
    await garrisons.process_garrisons(world)

    assert world.get_garrison(town.zone_id) is None
    assert world.get_garrison(hex_zone_id(land)) is None
