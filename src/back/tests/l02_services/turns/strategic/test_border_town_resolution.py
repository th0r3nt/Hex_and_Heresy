"""
Судьба побежденного пограничного города в сервисном слое: четыре сценария
резолюции, блокировка армии на время работ и обратный отсчет на такте.
"""

from random import Random

import pytest

from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.exceptions.factions import (
    BorderTownNotFoundError,
    BorderTownOperationInProgressError,
    BorderTownResolutionInvalidError,
)
from src.back.l01_domain.exceptions.workers import InvalidAssignmentTargetError
from src.back.l01_domain.factions.constants import (
    BORDER_TOWN_RESOLUTION_TICKS,
    BorderTownResolutionType,
    BuildingCategory,
    OCCUPY_LEVEL_DOWNGRADE,
    PILLAGE_BUILDINGS_DESTROY_MAX,
    PILLAGE_BUILDINGS_DESTROY_MIN,
    PILLAGE_LEVEL_DOWNGRADE,
    ResourceType,
)
from src.back.l01_domain.factions.models.border_town import BorderTown
from src.back.l01_domain.factions.models.buildings import (
    Building,
    ConstructedBuilding,
    RegionalHall,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.garrison import Garrison
from src.back.l01_domain.maps.constants import TerritoryZoneType
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    hex_neighbors,
    hex_zone_id,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.settlements.facade import SettlementsFacade
from src.back.utils.event.registry import GameEvents

TOWN_HEX = HexCoordinates.from_axial(3, -5)
TOWN_LAND_HEX = hex_neighbors(TOWN_HEX)[0]

INVESTED = {
    ResourceType.GOLD: 1000.0,
    ResourceType.MATERIAL: 400.0,
    ResourceType.FOOD: 200.0,
}


# ==================================================================
# ВСПОМОГАТЕЛЬНОЕ
# ==================================================================


def _add_building(faction: Faction, zone_id: str, name: str) -> ConstructedBuilding:
    """Ставит фракции готовую постройку на указанной земле."""
    building = ConstructedBuilding(
        building=Building(
            id=f"bld_{name}",
            faction_id=faction.race_id,
            name=name,
            category=BuildingCategory.ECONOMIC,
            allowed_zone=TerritoryZoneType.ALLIED_LANDS,
        ),
        zone_id=zone_id,
        is_under_construction=False,
    )
    faction.add_building(building)
    return building


@pytest.fixture
def town(human_faction: Faction) -> BorderTown:
    """
    Город второго уровня с одной выкупленной землей, тремя постройками
    внутри стен и одной - на союзной земле.
    """
    settlement = BorderTown(
        faction_id=human_faction.id,
        name="Врата висельников",
        center_hex=TOWN_HEX,
        level=3,
    )
    settlement.register_investment(INVESTED)
    settlement.claim_land(TOWN_LAND_HEX)

    human_faction.add_border_town(settlement)
    human_faction.gain_zone(settlement.zone_id)
    human_faction.gain_zone(hex_zone_id(TOWN_LAND_HEX))
    human_faction.add_regional_hall(
        RegionalHall(
            faction_id=human_faction.id,
            zone_id=hex_zone_id(TOWN_LAND_HEX),
            name="Ратуша поселения",
            level=2,
        )
    )

    for index in range(3):
        _add_building(human_faction, settlement.zone_id, f"town_{index}")
    _add_building(human_faction, hex_zone_id(TOWN_LAND_HEX), "land_0")

    return settlement


@pytest.fixture
def world(human_faction: Faction, orc_faction: Faction, town: BorderTown) -> WorldState:
    """
    Мир сразу после штурма: гарнизон города выбит подчистую, а на его
    гексе стоит войско орков.
    """
    state = WorldState()
    state.add_faction(human_faction)
    state.add_faction(orc_faction)
    state.neutral_hexes = []

    state.add_garrison(
        Garrison(
            zone_id=town.zone_id,
            faction_id=human_faction.id,
            hex_coordinates=TOWN_HEX,
        )
    )
    state.add_army(
        StrategicArmy(
            id="orc-horde",
            faction_id=orc_faction.id,
            name="Орда Ржавых Клыков",
            current_hex=TOWN_HEX,
        )
    )
    return state


@pytest.fixture
def service(fake_bus) -> SettlementsFacade:
    """
    Сервис с предсказуемым жребием: разграбление должно сносить одни и те
    же постройки от запуска к запуску.
    """
    return SettlementsFacade(event_bus=fake_bus, rng=Random(1))


async def _run_to_the_end(
    service: SettlementsFacade, world: WorldState, resolution_type: BorderTownResolutionType
):
    """Прожигает столько тактов, сколько длится сценарий, и отдает отчет."""
    report = None
    for _ in range(BORDER_TOWN_RESOLUTION_TICKS[resolution_type]):
        report = await service.process_town_resolutions(world)
    return report


def _published(fake_bus, event) -> list[dict]:
    """Полезная нагрузка всех публикаций одного события."""
    return [payload for name, payload in fake_bus.events if name == event]


# ==================================================================
# НАЧАЛО ОПЕРАЦИИ
# ==================================================================


@pytest.mark.asyncio
async def test_started_operation_pins_the_army_to_the_town(
    service: SettlementsFacade, world: WorldState, town: BorderTown
):
    """Начатая операция приковывает армию победителя к гексу города."""
    operation = await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.RAZE,
    )

    army = world.get_army("orc-horde")
    assert operation is not None
    assert army.is_busy_with_operation
    assert army.active_operation_id == operation.id
    assert world.get_town_operation(town.id) is operation


@pytest.mark.asyncio
async def test_started_operation_freezes_the_town_garrison(
    service: SettlementsFacade, world: WorldState, town: BorderTown
):
    """Пока победитель хозяйничает в стенах, ополчение не набирается."""
    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.PILLAGE,
    )

    assert world.get_garrison(town.zone_id).is_locked_in_resolution


@pytest.mark.asyncio
async def test_start_is_announced_to_the_party(
    service: SettlementsFacade, world: WorldState, town: BorderTown, fake_bus
):
    """О начале операции партия узнает событием."""
    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.OCCUPY,
    )

    events = _published(fake_bus, GameEvents.Economy.BORDER_TOWN_RESOLUTION_STARTED)
    assert len(events) == 1
    assert events[0]["town_id"] == town.id
    assert events[0]["resolution_type"] == BorderTownResolutionType.OCCUPY.value
    assert events[0]["ticks_total"] == 2


# ==================================================================
# СЦЕНАРИЙ Г: ПРОПУСК
# ==================================================================


@pytest.mark.asyncio
async def test_ignored_town_is_left_exactly_as_it_was(
    service: SettlementsFacade,
    world: WorldState,
    town: BorderTown,
    human_faction: Faction,
    orc_faction: Faction,
):
    """
    Пропуск ничего не меняет: армия свободна тем же тактом, город цел, а
    в казну победителя не приходит ни монеты.
    """
    treasury_before = dict(orc_faction.resources)

    operation = await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.IGNORE,
    )

    assert operation is None
    assert world.border_town_operations == {}
    assert not world.get_army("orc-horde").is_busy_with_operation
    assert not world.get_garrison(town.zone_id).is_locked_in_resolution
    assert human_faction.get_border_town(town.id) is town
    assert town.level == 3
    assert len(human_faction.buildings) == 4
    assert orc_faction.resources == treasury_before


# ==================================================================
# СЦЕНАРИЙ А: РАЗРУШЕНИЕ
# ==================================================================


@pytest.mark.asyncio
async def test_razing_takes_three_ticks_and_only_then_burns_the_town(
    service: SettlementsFacade,
    world: WorldState,
    town: BorderTown,
    human_faction: Faction,
):
    """Два первых такта город еще стоит: сжечь его - работа на три такта."""
    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.RAZE,
    )

    for _ in range(2):
        report = await service.process_town_resolutions(world)
        assert report.razed_town_ids == []
        assert human_faction.get_border_town(town.id) is town
        assert world.get_army("orc-horde").is_busy_with_operation

    report = await service.process_town_resolutions(world)

    assert report.razed_town_ids == [town.id]
    assert human_faction.get_border_town(town.id) is None
    assert not world.get_army("orc-horde").is_busy_with_operation
    assert report.released_army_ids == ["orc-horde"]


@pytest.mark.asyncio
async def test_razing_returns_every_hex_of_the_town_to_no_mans_land(
    service: SettlementsFacade,
    world: WorldState,
    town: BorderTown,
    human_faction: Faction,
):
    """
    От сожженного города не остается ничего: ни построек, ни ратуш, ни
    гарнизонов - все его гексы возвращаются в Ничью землю.
    """
    land_zone_id = hex_zone_id(TOWN_LAND_HEX)

    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.RAZE,
    )
    await _run_to_the_end(service, world, BorderTownResolutionType.RAZE)

    assert human_faction.border_towns == []
    assert human_faction.controlled_zone_ids == []
    assert human_faction.regional_halls == []
    assert human_faction.buildings == []
    assert world.get_garrison(town.zone_id) is None
    assert world.get_garrison(land_zone_id) is None
    assert TOWN_HEX in world.neutral_hexes
    assert TOWN_LAND_HEX in world.neutral_hexes


@pytest.mark.asyncio
async def test_razing_pays_the_conqueror_half_the_investments(
    service: SettlementsFacade, world: WorldState, town: BorderTown, orc_faction: Faction
):
    """За сожженный город победитель уносит половину всех вложений."""
    gold_before = orc_faction.resources[ResourceType.GOLD]

    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.RAZE,
    )
    await _run_to_the_end(service, world, BorderTownResolutionType.RAZE)

    expected = gold_before + INVESTED[ResourceType.GOLD] * 0.5
    assert orc_faction.resources[ResourceType.GOLD] == pytest.approx(expected)


# ==================================================================
# СЦЕНАРИЙ Б: РАЗГРАБЛЕНИЕ
# ==================================================================


@pytest.mark.asyncio
async def test_pillaging_takes_two_ticks_and_leaves_the_town_to_its_owner(
    service: SettlementsFacade,
    world: WorldState,
    town: BorderTown,
    human_faction: Faction,
):
    """
    Разграбленный город остается прежнему хозяину - только обескровленным
    и на два уровня ниже.
    """
    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.PILLAGE,
    )

    first = await service.process_town_resolutions(world)
    assert first.pillaged_town_ids == []
    assert world.get_army("orc-horde").is_busy_with_operation

    second = await service.process_town_resolutions(world)

    assert second.pillaged_town_ids == [town.id]
    assert human_faction.get_border_town(town.id) is town
    assert town.faction_id == human_faction.id
    assert town.level == 3 - PILLAGE_LEVEL_DOWNGRADE
    assert not world.get_army("orc-horde").is_busy_with_operation
    assert not world.get_garrison(town.zone_id).is_locked_in_resolution


@pytest.mark.asyncio
async def test_pillaging_burns_two_or_three_buildings_inside_the_walls(
    service: SettlementsFacade,
    world: WorldState,
    town: BorderTown,
    human_faction: Faction,
    fake_bus,
):
    """
    Грабители жгут от двух до трех построек внутри стен и не трогают
    союзную землю города.
    """
    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.PILLAGE,
    )
    await _run_to_the_end(service, world, BorderTownResolutionType.PILLAGE)

    burned = _published(fake_bus, GameEvents.Economy.BORDER_TOWN_PILLAGED)[0][
        "destroyed_building_ids"
    ]
    assert PILLAGE_BUILDINGS_DESTROY_MIN <= len(burned) <= PILLAGE_BUILDINGS_DESTROY_MAX

    survivors = human_faction.buildings
    assert len(survivors) == 4 - len(burned)
    assert any(b.zone_id == hex_zone_id(TOWN_LAND_HEX) for b in survivors), (
        "постройка союзной земли разграблению не подлежит"
    )


@pytest.mark.asyncio
async def test_pillaging_pays_the_conqueror_three_quarters(
    service: SettlementsFacade, world: WorldState, town: BorderTown, orc_faction: Faction
):
    """Разграбление - самый выгодный исход: три четверти всех вложений."""
    gold_before = orc_faction.resources[ResourceType.GOLD]

    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.PILLAGE,
    )
    await _run_to_the_end(service, world, BorderTownResolutionType.PILLAGE)

    expected = gold_before + INVESTED[ResourceType.GOLD] * 0.75
    assert orc_faction.resources[ResourceType.GOLD] == pytest.approx(expected)


# ==================================================================
# СЦЕНАРИЙ В: ЗАХВАТ
# ==================================================================


@pytest.mark.asyncio
async def test_occupied_town_changes_hands_with_all_its_lands(
    service: SettlementsFacade,
    world: WorldState,
    town: BorderTown,
    human_faction: Faction,
    orc_faction: Faction,
):
    """
    Вместе с городом к победителю переходят его земли и стоящие на них
    ратуши, а прежний хозяин теряет и то, и другое.
    """
    land_zone_id = hex_zone_id(TOWN_LAND_HEX)

    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.OCCUPY,
    )
    report = await _run_to_the_end(service, world, BorderTownResolutionType.OCCUPY)

    assert report.occupied_town_ids == [town.id]
    assert human_faction.border_towns == []
    assert human_faction.controlled_zone_ids == []
    assert human_faction.regional_halls == []

    assert orc_faction.get_border_town(town.id) is town
    assert town.faction_id == orc_faction.id
    assert town.level == 3 - OCCUPY_LEVEL_DOWNGRADE
    assert set(orc_faction.controlled_zone_ids) == {town.zone_id, land_zone_id}

    hall = orc_faction.get_regional_hall(land_zone_id)
    assert hall is not None and hall.faction_id == orc_faction.id
    assert hall.level == 2, "ратуша переезжает как есть, а не отстраивается заново"


@pytest.mark.asyncio
async def test_occupation_leaves_the_conqueror_bare_walls(
    service: SettlementsFacade,
    world: WorldState,
    town: BorderTown,
    human_faction: Faction,
):
    """
    Внутри захваченного города не остается ни одной постройки, а вот на
    союзной земле они переходят новому хозяину целыми.
    """
    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.OCCUPY,
    )
    await _run_to_the_end(service, world, BorderTownResolutionType.OCCUPY)

    assert [b.zone_id for b in human_faction.buildings] == [hex_zone_id(TOWN_LAND_HEX)]


@pytest.mark.asyncio
async def test_occupation_rebinds_the_garrison_to_the_new_owner(
    service: SettlementsFacade,
    world: WorldState,
    town: BorderTown,
    orc_faction: Faction,
    basic_squad,
):
    """
    Гарнизон меняет флаг, но прежних защитников в нем не остается: свое
    ополчение новый хозяин поднимет сам на ближайшем такте.
    """
    # Выбитый под ноль отряд из гарнизона не исчезает - он ждет пополнения,
    # которого при смене хозяина уже не будет
    basic_squad.state.unit_count = 0
    world.get_garrison(town.zone_id).stationed_squads.append(basic_squad)

    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.OCCUPY,
    )
    await _run_to_the_end(service, world, BorderTownResolutionType.OCCUPY)

    garrison = world.get_garrison(town.zone_id)
    assert garrison.faction_id == orc_faction.id
    assert garrison.all_squads == []
    assert not garrison.is_locked_in_resolution


@pytest.mark.asyncio
async def test_occupation_pays_the_conqueror_only_a_quarter(
    service: SettlementsFacade, world: WorldState, town: BorderTown, orc_faction: Faction
):
    """За целый город победитель получает всего четверть вложений."""
    gold_before = orc_faction.resources[ResourceType.GOLD]

    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.OCCUPY,
    )
    await _run_to_the_end(service, world, BorderTownResolutionType.OCCUPY)

    expected = gold_before + INVESTED[ResourceType.GOLD] * 0.25
    assert orc_faction.resources[ResourceType.GOLD] == pytest.approx(expected)


# ==================================================================
# ОТКАЗЫ
# ==================================================================


@pytest.mark.asyncio
async def test_unknown_town_cannot_be_resolved(
    service: SettlementsFacade, world: WorldState
):
    """Судьбу несуществующего города решать не о чем."""
    with pytest.raises(BorderTownNotFoundError):
        await service.initiate_town_resolution(
            world_state=world,
            town_id="town-that-never-was",
            army_id="orc-horde",
            resolution_type=BorderTownResolutionType.RAZE,
        )


@pytest.mark.asyncio
async def test_unknown_army_cannot_be_resolved(
    service: SettlementsFacade, world: WorldState, town: BorderTown
):
    """Без армии-победителя приказ отдавать некому."""
    with pytest.raises(InvalidAssignmentTargetError):
        await service.initiate_town_resolution(
            world_state=world,
            town_id=town.id,
            army_id="ghost-army",
            resolution_type=BorderTownResolutionType.RAZE,
        )


@pytest.mark.asyncio
async def test_own_town_is_not_a_prize(
    service: SettlementsFacade,
    world: WorldState,
    town: BorderTown,
    human_faction: Faction,
):
    """Свой собственный город не грабят."""
    world.add_army(
        StrategicArmy(
            id="human-legion",
            faction_id=human_faction.id,
            name="Первый легион",
            current_hex=TOWN_HEX,
        )
    )

    with pytest.raises(BorderTownResolutionInvalidError):
        await service.initiate_town_resolution(
            world_state=world,
            town_id=town.id,
            army_id="human-legion",
            resolution_type=BorderTownResolutionType.PILLAGE,
        )


@pytest.mark.asyncio
async def test_army_must_stand_on_the_town_hex(
    service: SettlementsFacade, world: WorldState, town: BorderTown
):
    """Город нельзя разорять, находясь от него в дне марша."""
    world.get_army("orc-horde").current_hex = HexCoordinates.from_axial(0, 0)

    with pytest.raises(BorderTownResolutionInvalidError):
        await service.initiate_town_resolution(
            world_state=world,
            town_id=town.id,
            army_id="orc-horde",
            resolution_type=BorderTownResolutionType.RAZE,
        )


@pytest.mark.asyncio
async def test_standing_garrison_still_holds_the_town(
    service: SettlementsFacade, world: WorldState, town: BorderTown, basic_squad
):
    """Пока в гарнизоне есть хоть один живой боец, город не взят."""
    world.get_garrison(town.zone_id).stationed_squads.append(basic_squad)

    with pytest.raises(BorderTownResolutionInvalidError):
        await service.initiate_town_resolution(
            world_state=world,
            town_id=town.id,
            army_id="orc-horde",
            resolution_type=BorderTownResolutionType.RAZE,
        )


@pytest.mark.asyncio
async def test_defender_army_on_the_hex_still_holds_the_town(
    service: SettlementsFacade,
    world: WorldState,
    town: BorderTown,
    human_faction: Faction,
    basic_squad,
):
    """
    Недобитое войско защитника на гексе города держит его не хуже
    гарнизона: решать судьбу поселения рано.
    """
    defender = StrategicArmy(
        faction_id=human_faction.id, name="Остатки гарнизона", current_hex=TOWN_HEX
    )
    defender.add_squad(basic_squad)
    world.add_army(defender)

    with pytest.raises(BorderTownResolutionInvalidError):
        await service.initiate_town_resolution(
            world_state=world,
            town_id=town.id,
            army_id="orc-horde",
            resolution_type=BorderTownResolutionType.RAZE,
        )


@pytest.mark.asyncio
async def test_town_is_not_shared_between_two_operations(
    service: SettlementsFacade,
    world: WorldState,
    town: BorderTown,
    orc_faction: Faction,
):
    """Два войска не могут жечь и грабить одно поселение разом."""
    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.RAZE,
    )
    world.add_army(
        StrategicArmy(
            id="second-horde",
            faction_id=orc_faction.id,
            name="Вторая орда",
            current_hex=TOWN_HEX,
        )
    )

    with pytest.raises(BorderTownOperationInProgressError):
        await service.initiate_town_resolution(
            world_state=world,
            town_id=town.id,
            army_id="second-horde",
            resolution_type=BorderTownResolutionType.PILLAGE,
        )


@pytest.mark.asyncio
async def test_busy_army_cannot_take_a_second_town(
    service: SettlementsFacade,
    world: WorldState,
    town: BorderTown,
    human_faction: Faction,
):
    """Занятая операцией армия второй город не разорит."""
    second_town = BorderTown(
        faction_id=human_faction.id,
        name="Второй город",
        center_hex=TOWN_HEX,
    )
    human_faction.add_border_town(second_town)

    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.RAZE,
    )

    with pytest.raises(BorderTownResolutionInvalidError):
        await service.initiate_town_resolution(
            world_state=world,
            town_id=second_town.id,
            army_id="orc-horde",
            resolution_type=BorderTownResolutionType.RAZE,
        )


# ==================================================================
# ЧТЕНИЕ ПРОГРЕССА
# ==================================================================


@pytest.mark.asyncio
async def test_operation_progress_is_readable_and_disappears_at_the_end(
    service: SettlementsFacade, world: WorldState, town: BorderTown
):
    """
    Окно осады видит обратный отсчет, а по завершении работ операции над
    городом больше нет.
    """
    assert service.get_town_operation(world, town.id) is None

    await service.initiate_town_resolution(
        world_state=world,
        town_id=town.id,
        army_id="orc-horde",
        resolution_type=BorderTownResolutionType.PILLAGE,
    )
    await service.process_town_resolutions(world)

    operation = service.get_town_operation(world, town.id)
    assert operation is not None and operation.ticks_remaining == 1

    await service.process_town_resolutions(world)

    assert service.get_town_operation(world, town.id) is None
