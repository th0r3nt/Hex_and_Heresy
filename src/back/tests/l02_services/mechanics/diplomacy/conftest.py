"""
Общие фикстуры для тестов дипломатии: фракции с цитаделями на карте,
фейковая шина событий.
"""

from typing import Any, Optional

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord, LordArchetype, LordTrait
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState

from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder

class FakePromptBuilder(PromptBuilder):
    """Имитирует сборку, отдавая вместо текста сами ключи путей."""
    def __init__(self):
        super().__init__()

    def build(self, keys: list[str]) -> str:
        return "\n\n".join(f"[{key}]" for key in keys)

@pytest.fixture
def fake_prompt_builder() -> FakePromptBuilder:
    return FakePromptBuilder()

class FakeEventBus:
    """Фейковая шина событий для фиксации опубликованных сообщений."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        self.events.append((event_name, kwargs))

    def names(self) -> list[str]:
        return [name for name, _ in self.events]


def _make_faction(
    faction_id: str,
    race: FactionRace,
    name: str,
    capital_hex: Optional[HexCoordinates],
    gold: float = 1000.0,
) -> Faction:
    lord = Lord(
        faction_id=faction_id,
        name=f"Лорд {name}",
        title="Правитель",
        archetype=LordArchetype(id=f"arch_{faction_id}", name="Прагматик", description="..."),
        trait=LordTrait(id=f"trait_{faction_id}", name="Расчетливый", text_fragment="..."),
    )
    faction = Faction(
        id=faction_id,
        race=race,
        name=name,
        lord=lord,
        headquarters=Headquarters(faction_id=faction_id, name="Цитадель"),
        capital_hex=capital_hex,
    )
    faction.resources[ResourceType.GOLD] = gold
    faction.resources[ResourceType.FOOD] = 500.0
    faction.resources[ResourceType.MATERIAL] = 500.0
    return faction


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def humans() -> Faction:
    """Цитадель людей в начале координат."""
    return _make_faction(
        "humans", FactionRace.HUMANS, "Священная Империя", HexCoordinates.from_axial(0, 0)
    )


@pytest.fixture
def elfs() -> Faction:
    """Цитадель эльфов в 8 гексах от людей - два такта пути гонца."""
    return _make_faction(
        "elfs", FactionRace.ELFS, "Дом Серебряного Листа", HexCoordinates.from_axial(8, 0)
    )


@pytest.fixture
def greenskins() -> Faction:
    """Зеленокожие без цитадели на карте - для проверок ошибок маршрута."""
    return _make_faction(
        "greenskins", FactionRace.GREENSKINS, "Орда Ржавых Клыков", None, gold=50.0
    )


@pytest.fixture
def world(humans: Faction, elfs: Faction, greenskins: Faction) -> WorldState:
    state = WorldState()
    state.add_faction(humans)
    state.add_faction(elfs)
    state.add_faction(greenskins)
    return state
