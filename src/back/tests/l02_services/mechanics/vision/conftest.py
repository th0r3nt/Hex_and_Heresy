"""
Окружение тестов подсистемы тумана войны.

Мир собирается вручную и по одной детали за раз: цитадель на известном
гексе, при необходимости - ратуша, вышка или армия. Так по результату
видно, какой именно источник обзора вскрыл сектор.

Геометрия здесь одномерная: обе цитадели стоят на оси r = 0 в двенадцати
гексах друг от друга, поэтому расстояния читаются прямо из координат.
"""

from typing import Optional

import pytest

from src.back.l01_domain.army.constants import (
    AccessoryCategory,
    EquipmentSlot,
)
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import BuildingCategory, ResourceType
from src.back.l01_domain.factions.models.buildings import (
    Building,
    ConstructedBuilding,
    Headquarters,
    RegionalHall,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.constants import (
    TerritoryZoneType,
    VISION_RADIUS_WATCHTOWER,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates, hex_zone_id
from src.back.l01_domain.world.models.state import WorldState

# Цитадели сторон и удобные ориентиры между ними
PLAYER_CAPITAL = HexCoordinates.from_axial(0, 0)
RIVAL_CAPITAL = HexCoordinates.from_axial(12, 0)


def hex_at(q: int, r: int = 0) -> HexCoordinates:
    """Короткий способ назвать гекс на оси экватора."""
    return HexCoordinates.from_axial(q, r)


class FakeEventBus:
    """Фейковая шина: тестам важно, о чем именно протрубили."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args, **kwargs) -> None:
        self.events.append((event_name, kwargs))

    def names(self) -> list[str]:
        return [name for name, _ in self.events]

    def payloads(self, event_name: str) -> list[dict]:
        return [payload for name, payload in self.events if name == event_name]


# ==================================================================
# СБОРКА ФРАКЦИЙ И ИХ ЗАСТРОЙКИ
# ==================================================================


def build_faction(
    faction_id: str,
    capital: HexCoordinates,
    is_player: bool = False,
) -> Faction:
    """Живая фракция с цитаделью на известном гексе и пустой периферией."""
    faction = Faction(
        id=faction_id,
        race=FactionRace.HUMANS,
        name=f"Держава {faction_id}",
        is_player_controlled=is_player,
        lord=Lord(faction_id=faction_id, name="Лорд", title="Правитель"),
        headquarters=Headquarters(faction_id=faction_id, name="Цитадель"),
        capital_hex=capital,
    )
    faction.resources[ResourceType.GOLD] = 100.0
    faction.gain_zone(hex_zone_id(capital))
    return faction


def add_regional_hall(faction: Faction, coord: HexCoordinates) -> RegionalHall:
    """Ставит фракции ратушу на союзной земле."""
    hall = RegionalHall(
        faction_id=faction.id, zone_id=hex_zone_id(coord), name="Ратуша"
    )
    faction.add_regional_hall(hall)
    faction.gain_zone(hall.zone_id)
    return hall


def add_watchtower(
    faction: Faction,
    coord: HexCoordinates,
    is_under_construction: bool = False,
    radius: int = VISION_RADIUS_WATCHTOWER,
) -> ConstructedBuilding:
    """
    Ставит сторожевую вышку - здание, которое само объявляет свой радиус обзора.
    """
    template = Building(
        id="test_watchtower",
        faction_id=faction.id,
        name="Смотровая вышка",
        category=BuildingCategory.DEFENSIVE,
        allowed_zone=TerritoryZoneType.ALLIED_LANDS,
        vision_radius_hexes=radius,
    )
    constructed = ConstructedBuilding(
        building=template,
        zone_id=hex_zone_id(coord),
        is_under_construction=is_under_construction,
    )
    faction.add_building(constructed)
    return constructed


# ==================================================================
# СБОРКА АРМИЙ
# ==================================================================


def build_squad(accessory: Optional[Equipment] = None) -> Squad:
    """Простейший отряд: тесту от него нужны только слоты снаряжения."""
    archetype = UnitArchetype(
        id="unit_scout",
        race=FactionRace.HUMANS,
        faction_id="humans",
        name="Разъезд",
        tier=1,
        default_unit_count=50,
        base_stats=BaseUnitStats(max_hp=20.0),
    )
    return Squad.create_new(archetype=archetype, accessory=accessory)


def build_lenses(vision_bonus: int = 1) -> Equipment:
    """Аксессуар-оптика, расширяющий обзор носителя."""
    return Equipment(
        id="acc_lenses",
        name="Линзы дальновидности",
        lore="Кристаллы, преломляющие свет",
        slot=EquipmentSlot.ACCESSORY,
        category=AccessoryCategory.MISC,
        tier=0,
        stats=EquipmentStats(vision_bonus_hexes=vision_bonus),
    )


def add_army(
    world_state: WorldState,
    faction_id: str,
    coord: HexCoordinates,
    squads: Optional[list[Squad]] = None,
    commander: Optional[Commander] = None,
    name: str = "Полк",
) -> StrategicArmy:
    """Ставит на карту армию фракции."""
    army = StrategicArmy(
        faction_id=faction_id,
        name=name,
        current_hex=coord,
        commander=commander,
    )
    for squad in squads or []:
        army.add_squad(squad)
    world_state.add_army(army)
    return army


# ==================================================================
# ФИКСТУРЫ
# ==================================================================


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def player() -> Faction:
    return build_faction("humans", PLAYER_CAPITAL, is_player=True)


@pytest.fixture
def rival() -> Faction:
    return build_faction("greenskins", RIVAL_CAPITAL)


@pytest.fixture
def world(player: Faction, rival: Faction) -> WorldState:
    """Партия двух сторон: цитадели на оси экватора, между ними Ничья земля."""
    world_state = WorldState()
    world_state.add_faction(player)
    world_state.add_faction(rival)
    return world_state
