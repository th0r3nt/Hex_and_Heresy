"""
Окружение тестов подсистемы глобальных целей.

Мир собирается вручную и минимальным: цитадель, немного казны и, где нужно,
пограничные города. Ничего лишнего в нем нет - иначе непонятно, какое
именно условие сработало.
"""

from typing import Optional

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.border_town import BorderTown
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState


class FakeEventBus:
    """Фейковая шина: тестам важно, о чем именно протрубили."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args, **kwargs) -> None:
        self.events.append((event_name, kwargs))

    def names(self) -> list[str]:
        return [name for name, _ in self.events]


def build_faction(
    faction_id: str,
    name: str,
    race: FactionRace = FactionRace.HUMANS,
    is_player: bool = False,
    gold: float = 100.0,
    material: float = 100.0,
    food: float = 100.0,
) -> Faction:
    """
    Живая фракция: цитадель на месте и в казне что-то есть - значит,
    из партии она не выбыла.
    """
    faction = Faction(
        id=faction_id,
        race=race,
        name=name,
        is_player_controlled=is_player,
        lord=Lord(faction_id=faction_id, name=f"Лорд {name}", title="Правитель"),
        headquarters=Headquarters(faction_id=faction_id, name="Цитадель"),
        capital_hex=HexCoordinates.from_axial(0, 0),
    )
    faction.resources[ResourceType.GOLD] = gold
    faction.resources[ResourceType.MATERIAL] = material
    faction.resources[ResourceType.FOOD] = food
    return faction


def add_towns(faction: Faction, levels: list[int]) -> list[BorderTown]:
    """Вешает на фракцию пограничные города заданных уровней."""
    towns: list[BorderTown] = []
    for index, level in enumerate(levels):
        town = BorderTown(
            faction_id=faction.id,
            name=f"Город-{index + 1}",
            level=level,
            center_hex=HexCoordinates.from_axial(5 + index, -5),
        )
        faction.add_border_town(town)
        towns.append(town)
    return towns


def ruin_faction(faction: Faction) -> None:
    """
    Разоряет фракцию дотла: ни земель, ни построек, ни единой монеты.
    Цитадель при этом формально цела.
    """
    faction.border_towns.clear()
    faction.regional_halls.clear()
    faction.controlled_zone_ids.clear()
    faction.buildings.clear()
    for resource in ResourceType:
        faction.resources[resource] = 0.0


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def player() -> Faction:
    return build_faction(
        "humans", "Священная Империя", FactionRace.HUMANS, is_player=True
    )


@pytest.fixture
def rival() -> Faction:
    return build_faction(
        "greenskins", "Орда Ржавых Клыков", FactionRace.GREENSKINS
    )


@pytest.fixture
def world(player: Faction, rival: Faction) -> WorldState:
    """Партия двух сторон: игрок и один соперник, оба живы."""
    world_state = WorldState()
    world_state.add_faction(player)
    world_state.add_faction(rival)
    return world_state


@pytest.fixture
def solo_world(player: Faction) -> WorldState:
    """Партия, в которой у игрока нет соперников вовсе."""
    world_state = WorldState()
    world_state.add_faction(player)
    return world_state


def player_of(world_state: WorldState) -> Optional[Faction]:
    return world_state.get_player_faction()
