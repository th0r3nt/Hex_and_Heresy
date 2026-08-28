"""
Сервис гарнизонов на глобальном такте: подъем ополчения под уровень
зданий, восстановление потерь, ротация войск и оборона земли.
"""

import pytest

from src.back.l01_domain.army.constants import StrategicMovementPace
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions.factions import (
    GarrisonCapacityExceededError,
    GarrisonNotFoundError,
    GarrisonRotationForbiddenError,
    ZoneNotControlledError,
)
from src.back.l01_domain.factions.constants import (
    MAX_STATIONED_GARRISON_SQUADS,
    MILITIA_CAPACITY_BY_LEVEL,
)
from src.back.l01_domain.factions.models.buildings import RegionalHall
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.constants import ALLIED_LANDS_RING_RADIUS
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    hex_ring,
    hex_zone_id,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.garrison import GarrisonService
from src.back.l03_infrastructure.gamedata.loader import build_static_registry
from src.back.utils.event.registry import GameEvents

CAPITAL_HEX = HexCoordinates.from_axial(4, -8)


# ==================================================================
# ФИКСТУРЫ
# ==================================================================


@pytest.fixture
def world(human_faction: Faction) -> WorldState:
    """Мир с одной фракцией, чья цитадель стоит на известном гексе."""
    human_faction.capital_hex = CAPITAL_HEX
    state = WorldState()
    state.add_faction(human_faction)
    return state


@pytest.fixture
def service(fake_bus) -> GarrisonService:
    """Сервис без каталога: ополчение поднимается резервным архетипом."""
    return GarrisonService(event_bus=fake_bus)


@pytest.fixture(scope="module")
def gamedata_registry():
    """
    Настоящий каталог игры: нужен ровно одному тесту - тому, что проверяет
    подъем ополчения из расового ростера, а не из резервного шаблона.
    """
    return build_static_registry()


def _allied_hex(index: int = 0) -> HexCoordinates:
    """Гекс союзной земли из лепестка вокруг цитадели."""
    return hex_ring(CAPITAL_HEX, ALLIED_LANDS_RING_RADIUS)[index]


def _grant_allied_zone(faction: Faction, coord: HexCoordinates, level: int = 1) -> str:
    """Отдает фракции союзную землю вместе с ратушей нужного уровня."""
    zone_id = hex_zone_id(coord)
    faction.gain_zone(zone_id)
    faction.add_regional_hall(
        RegionalHall(faction_id=faction.id, zone_id=zone_id, name="Ратуша", level=level)
    )
    return zone_id


def _army(world: WorldState, faction: Faction, at: HexCoordinates) -> StrategicArmy:
    army = StrategicArmy(
        faction_id=faction.id,
        name="Полевая армия",
        current_hex=at,
        pace=StrategicMovementPace.MARCH,
    )
    world.add_army(army)
    return army


def _line_squad(tier: int = 3) -> Squad:
    """Регулярный отряд, который игрок может оставить за стенами."""
    return Squad.create_new(
        archetype=UnitArchetype(
            id=f"unit_test_line_{tier}",
            race=FactionRace.HUMANS,
            faction_id="humans",
            name="Железнобокие",
            tier=tier,
            default_unit_count=80,
            base_stats=BaseUnitStats(max_hp=25.0),
            base_upkeep_food=1.0,
            base_upkeep_gold=1.0,
        )
    )


# ==================================================================
# ПОДЪЕМ ГАРНИЗОНОВ НА ТАКТЕ
# ==================================================================


@pytest.mark.asyncio
async def test_citadel_raises_its_garrison_on_first_tick(
    service: GarrisonService, world: WorldState, human_faction: Faction
):
    """Гекс цитадели получает несносимый гарнизон без всякого приказа."""
    report = await service.process_garrisons(world)

    zone_id = hex_zone_id(CAPITAL_HEX)
    garrison = world.get_garrison(zone_id)

    assert zone_id in report.raised_garrison_zone_ids
    assert garrison is not None
    assert garrison.faction_id == human_faction.id
    assert len(garrison.militia_squads) == MILITIA_CAPACITY_BY_LEVEL[1]


@pytest.mark.asyncio
async def test_allied_land_with_a_hall_gets_its_own_garrison(
    service: GarrisonService, world: WorldState, human_faction: Faction
):
    """Союзная земля с ратушей обороняется собственным ополчением."""
    zone_id = _grant_allied_zone(human_faction, _allied_hex())

    await service.process_garrisons(world)

    assert world.get_garrison(zone_id) is not None
    assert len(world.get_faction_garrisons(human_faction.id)) == 2


@pytest.mark.asyncio
async def test_allied_land_without_a_hall_stays_undefended(
    service: GarrisonService, world: WorldState, human_faction: Faction
):
    """Пустая земля без административного центра ополчение не поднимает."""
    coord = _allied_hex()
    human_faction.gain_zone(hex_zone_id(coord))

    await service.process_garrisons(world)

    assert world.get_garrison(hex_zone_id(coord)) is None


@pytest.mark.asyncio
async def test_citadel_upgrade_opens_a_militia_slot(
    service: GarrisonService, world: WorldState, human_faction: Faction
):
    """Апгрейд цитадели тем же тактом добавляет отряд ополчения."""
    await service.process_garrisons(world)
    human_faction.headquarters.upgrade()

    report = await service.process_garrisons(world)

    garrison = world.get_garrison(hex_zone_id(CAPITAL_HEX))
    assert len(garrison.militia_squads) == MILITIA_CAPACITY_BY_LEVEL[2]
    assert len(report.raised_militia_squad_ids) == 1


@pytest.mark.asyncio
async def test_lost_land_loses_its_garrison(
    service: GarrisonService, world: WorldState, human_faction: Faction
):
    """Отбитый врагом гекс перестает содержать чужое ополчение."""
    coord = _allied_hex()
    zone_id = _grant_allied_zone(human_faction, coord)
    await service.process_garrisons(world)

    human_faction.lose_zone(zone_id)
    report = await service.process_garrisons(world)

    assert zone_id in report.disbanded_garrison_zone_ids
    assert world.get_garrison(zone_id) is None


@pytest.mark.asyncio
async def test_militia_heals_between_assaults(
    service: GarrisonService, world: WorldState
):
    """После штурма ополчение само добирает потери такт за тактом."""
    await service.process_garrisons(world)
    garrison = world.get_garrison(hex_zone_id(CAPITAL_HEX))
    wounded = garrison.militia_squads[0]
    wounded.state.unit_count = 1

    report = await service.process_garrisons(world)

    assert wounded.id in report.replenished_militia_squad_ids
    assert wounded.state.unit_count > 1


@pytest.mark.asyncio
async def test_militia_does_not_heal_during_the_assault(
    service: GarrisonService, world: WorldState
):
    """Посреди штурма горожан обучать некогда."""
    await service.process_garrisons(world)
    garrison = world.get_garrison(hex_zone_id(CAPITAL_HEX))
    garrison.is_locked_in_battle = True
    wounded = garrison.militia_squads[0]
    wounded.state.unit_count = 1

    report = await service.process_garrisons(world)

    assert report.replenished_militia_squad_ids == []
    assert wounded.state.unit_count == 1


@pytest.mark.asyncio
async def test_faction_without_capital_gets_no_garrisons(
    service: GarrisonService, world: WorldState, human_faction: Faction
):
    """Без известной столицы гарнизону не на чем стоять."""
    human_faction.capital_hex = None

    report = await service.process_garrisons(world)

    assert report.raised_garrison_zone_ids == []
    assert world.garrisons == {}


# ==================================================================
# ОПОЛЧЕНИЕ ИЗ КАТАЛОГА РАСЫ
# ==================================================================


@pytest.mark.asyncio
async def test_militia_is_recruited_from_the_race_roster(
    world: WorldState, fake_bus, gamedata_registry
):
    """Ополчение поднимается расовым рецептом найма, а не безликой толпой."""
    service = GarrisonService(gamedata=gamedata_registry, event_bus=fake_bus)

    await service.process_garrisons(world)

    militia = world.get_garrison(hex_zone_id(CAPITAL_HEX)).militia_squads
    assert militia, "ополчение не поднялось"
    for squad in militia:
        assert squad.archetype.faction_id == "humans"
        assert squad.archetype.tier in (1, 2)
        assert squad.weapon is not None, "ополчение вышло с голыми руками"


# ==================================================================
# РОТАЦИЯ ВОЙСК
# ==================================================================


@pytest.mark.asyncio
async def test_stationing_moves_the_squad_from_army_to_walls(
    service: GarrisonService, world: WorldState, human_faction: Faction, fake_bus
):
    """Отряд физически уходит из армии в гарнизон, а не копируется в него."""
    await service.process_garrisons(world)
    army = _army(world, human_faction, CAPITAL_HEX)
    squad = _line_squad()
    army.add_squad(squad)

    zone_id = hex_zone_id(CAPITAL_HEX)
    garrison = await service.station_squad(
        world_state=world, army_id=army.id, squad_id=squad.id, zone_id=zone_id
    )

    assert garrison.stationed_squads == [squad]
    assert army.squads == []
    assert GameEvents.Strategic.SQUAD_STATIONED in [name for name, _ in fake_bus.events]


@pytest.mark.asyncio
async def test_unstationing_returns_the_squad_to_the_army(
    service: GarrisonService, world: WorldState, human_faction: Faction
):
    """Забранный из гарнизона отряд возвращается в армию тем же объектом."""
    await service.process_garrisons(world)
    army = _army(world, human_faction, CAPITAL_HEX)
    squad = _line_squad()
    army.add_squad(squad)
    zone_id = hex_zone_id(CAPITAL_HEX)
    await service.station_squad(
        world_state=world, army_id=army.id, squad_id=squad.id, zone_id=zone_id
    )

    returned = await service.unstation_squad(
        world_state=world, army_id=army.id, squad_id=squad.id, zone_id=zone_id
    )

    assert returned is squad
    assert army.squads == [squad]
    assert world.get_garrison(zone_id).stationed_squads == []


@pytest.mark.asyncio
async def test_eleventh_stationed_squad_leaves_the_army_untouched(
    service: GarrisonService, world: WorldState, human_faction: Faction
):
    """
    Отказ по лимиту не должен потерять отряд: он остается в армии,
    а не растворяется между ней и гарнизоном.
    """
    await service.process_garrisons(world)
    zone_id = hex_zone_id(CAPITAL_HEX)
    garrison = world.get_garrison(zone_id)
    for _ in range(MAX_STATIONED_GARRISON_SQUADS):
        garrison.station_squad(_line_squad())

    army = _army(world, human_faction, CAPITAL_HEX)
    extra = _line_squad()
    army.add_squad(extra)

    with pytest.raises(GarrisonCapacityExceededError):
        await service.station_squad(
            world_state=world, army_id=army.id, squad_id=extra.id, zone_id=zone_id
        )

    assert army.squads == [extra]
    assert len(garrison.stationed_squads) == MAX_STATIONED_GARRISON_SQUADS


@pytest.mark.asyncio
async def test_distant_army_cannot_station_its_squads(
    service: GarrisonService, world: WorldState, human_faction: Faction
):
    """Оставить отряд в крепости, стоя в трех днях марша от нее, нельзя."""
    await service.process_garrisons(world)
    army = _army(world, human_faction, HexCoordinates.from_axial(0, 0))
    squad = _line_squad()
    army.add_squad(squad)

    with pytest.raises(GarrisonRotationForbiddenError):
        await service.station_squad(
            world_state=world,
            army_id=army.id,
            squad_id=squad.id,
            zone_id=hex_zone_id(CAPITAL_HEX),
        )


@pytest.mark.asyncio
async def test_army_in_battle_cannot_rotate_the_garrison(
    service: GarrisonService, world: WorldState, human_faction: Faction
):
    """Связанная боем армия не заводит и не выводит войска за стены."""
    await service.process_garrisons(world)
    army = _army(world, human_faction, CAPITAL_HEX)
    squad = _line_squad()
    army.add_squad(squad)
    army.lock_in_tactical_battle()

    with pytest.raises(GarrisonRotationForbiddenError):
        await service.station_squad(
            world_state=world,
            army_id=army.id,
            squad_id=squad.id,
            zone_id=hex_zone_id(CAPITAL_HEX),
        )


@pytest.mark.asyncio
async def test_foreign_army_cannot_enter_the_walls(
    service: GarrisonService, world: WorldState, orc_faction: Faction
):
    """Чужая армия не расквартировывается в чужой крепости."""
    await service.process_garrisons(world)
    world.add_faction(orc_faction)
    army = _army(world, orc_faction, CAPITAL_HEX)
    squad = _line_squad()
    army.add_squad(squad)

    with pytest.raises(ZoneNotControlledError):
        await service.station_squad(
            world_state=world,
            army_id=army.id,
            squad_id=squad.id,
            zone_id=hex_zone_id(CAPITAL_HEX),
        )


@pytest.mark.asyncio
async def test_rotation_on_a_land_without_garrison_fails(
    service: GarrisonService, world: WorldState, human_faction: Faction
):
    army = _army(world, human_faction, CAPITAL_HEX)
    squad = _line_squad()
    army.add_squad(squad)

    with pytest.raises(GarrisonNotFoundError):
        await service.station_squad(
            world_state=world, army_id=army.id, squad_id=squad.id, zone_id="99,99"
        )


# ==================================================================
# ОБОРОНА ЗЕМЛИ
# ==================================================================


@pytest.mark.asyncio
async def test_defenders_include_militia_and_stationed_troops(
    service: GarrisonService, world: WorldState
):
    """В бой на гексе базы выходит весь гарнизон целиком."""
    await service.process_garrisons(world)
    garrison = world.get_garrison(hex_zone_id(CAPITAL_HEX))
    stationed = _line_squad()
    garrison.station_squad(stationed)

    defenders = service.collect_defenders(world, CAPITAL_HEX)

    assert len(defenders) == len(garrison.militia_squads) + 1
    assert stationed in defenders


def test_empty_hex_has_no_defenders(service: GarrisonService, world: WorldState):
    assert service.collect_defenders(world, HexCoordinates.from_axial(0, 0)) == []
