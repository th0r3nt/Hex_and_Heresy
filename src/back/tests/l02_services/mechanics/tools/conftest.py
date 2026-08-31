"""
Общие фикстуры интеграционных тестов исполнителя навыков.

Здесь собирается настоящий сервисный слой: фасады те же, что в корне
компоновки, - подменены только шина событий и языковая модель. Проверяется
стык, а не логика механик: пришедший `ToolCall` обязан доехать до метода
фасада и изменить мир.
"""

from typing import Any, Optional

import pytest

from src.back.l01_domain.army.constants import StrategicMovementPace
from src.back.l01_domain.combat.models.state import TacticalBattleState, TacticalCellState
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.advisor.facade import AdvisorFacade
from src.back.l02_services.mechanics.chronicler.facade import ChroniclerFacade
from src.back.l02_services.mechanics.diplomacy.facade import DiplomacyFacade
from src.back.l02_services.mechanics.game_master.facade import GameMasterFacade
from src.back.l02_services.mechanics.gunsmith.facade import GunsmithFacade
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.l02_services.mechanics.tools.factory import build_tool_executor
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.tests.l02_services.fakes import FakeContextBuilder, FakePromptBuilder


# ==================================================================
# ФЕЙКОВОЕ ОКРУЖЕНИЕ
# ==================================================================


class FakeEventBus:
    """Шина событий, запоминающая опубликованное."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        self.events.append((event_name, kwargs))

    def names(self) -> list[str]:
        return [name for name, _ in self.events]

    def payload_of(self, event_name: str) -> dict:
        for name, payload in self.events:
            if name == event_name:
                return payload
        return {}


class SilentLLM:
    """
    Модель, которую обработчику навыка дергать незачем.

    Решение модель уже приняла - вызовом навыка; обработчик только переносит
    его на мир. Любое обращение к модели здесь - ошибка проектирования.
    """

    async def generate_text(self, *args: Any, **kwargs: Any) -> str:
        raise AssertionError("Обработчик навыка обратился к языковой модели")

    async def generate_structured(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Обработчик навыка обратился к языковой модели")

    async def generate_with_tools(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Обработчик навыка обратился к языковой модели")


# ==================================================================
# ИГРОВОЙ МИР
# ==================================================================


def _faction(
    faction_id: str,
    race: FactionRace,
    name: str,
    capital: Optional[HexCoordinates],
    is_player: bool = False,
) -> Faction:
    faction = Faction(
        id=faction_id,
        race=race,
        name=name,
        lord=Lord(faction_id=faction_id, name=f"Лорд {name}", title="Правитель"),
        headquarters=Headquarters(faction_id=faction_id, name="Цитадель"),
        capital_hex=capital,
        is_player_controlled=is_player,
    )
    faction.resources[ResourceType.GOLD] = 1000.0
    faction.resources[ResourceType.MATERIAL] = 1000.0
    faction.resources[ResourceType.FOOD] = 500.0
    return faction


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def humans() -> Faction:
    """Держава игрока: от ее лица модель и зовет навыки."""
    return _faction(
        "humans",
        FactionRace.HUMANS,
        "Священная Империя",
        HexCoordinates.from_axial(0, 0),
        is_player=True,
    )


@pytest.fixture
def elfs() -> Faction:
    """Соседи в восьми гексах: два такта пути гонца."""
    return _faction(
        "elfs", FactionRace.ELFS, "Дом Серебряного Листа", HexCoordinates.from_axial(8, 0)
    )


@pytest.fixture
def legion(humans: Faction) -> StrategicArmy:
    """Полевая армия игрока у столицы."""
    return StrategicArmy(
        faction_id=humans.id,
        name="1-й Легион",
        current_hex=HexCoordinates.from_axial(0, 0),
        pace=StrategicMovementPace.MARCH,
    )


@pytest.fixture
def world(humans: Faction, elfs: Faction, legion: StrategicArmy) -> WorldState:
    state = WorldState()
    state.add_faction(humans)
    state.add_faction(elfs)
    state.add_army(legion)
    return state


@pytest.fixture
def battle() -> TacticalBattleState:
    """Поле боя с одним отрядом на клетке (1, 1)."""
    return TacticalBattleState(
        cells=[
            TacticalCellState(coordinates=CellCoordinates(x=x, y=y))
            for x in range(4)
            for y in range(4)
        ]
    )


@pytest.fixture
def deployed_squad(battle: TacticalBattleState) -> str:
    """Ставит отряд на поле и отдает его идентификатор."""
    cell = battle.get_cell(CellCoordinates(x=1, y=1))
    cell.occupant_squad_id = "sq_guards"
    return "sq_guards"


# ==================================================================
# ФАСАДЫ СЕРВИСНОГО СЛОЯ
# ==================================================================


@pytest.fixture
def turns_facade(fake_bus: FakeEventBus) -> TurnsFacade:
    return TurnsFacade(event_bus=fake_bus)


@pytest.fixture
def diplomacy_facade(fake_bus: FakeEventBus) -> DiplomacyFacade:
    return DiplomacyFacade(event_bus=fake_bus)


@pytest.fixture
def gunsmith_facade(fake_bus: FakeEventBus) -> GunsmithFacade:
    return GunsmithFacade(
        llm_client=SilentLLM(),
        prompt_builder=FakePromptBuilder(),
        context_builder=FakeContextBuilder(),
        event_bus=fake_bus,
    )


@pytest.fixture
def game_master_facade(fake_bus: FakeEventBus) -> GameMasterFacade:
    return GameMasterFacade(
        llm_client=SilentLLM(),
        prompt_builder=FakePromptBuilder(),
        context_builder=FakeContextBuilder(),
        event_bus=fake_bus,
    )


@pytest.fixture
def chronicler_facade(fake_bus: FakeEventBus) -> ChroniclerFacade:
    return ChroniclerFacade(event_bus=fake_bus)


@pytest.fixture
def advisor_facade(fake_bus: FakeEventBus) -> AdvisorFacade:
    return AdvisorFacade(
        llm_client=SilentLLM(),
        prompt_builder=FakePromptBuilder(),
        context_builder=FakeContextBuilder(),
        event_bus=fake_bus,
    )


@pytest.fixture
def executor(
    turns_facade: TurnsFacade,
    diplomacy_facade: DiplomacyFacade,
    gunsmith_facade: GunsmithFacade,
    game_master_facade: GameMasterFacade,
    chronicler_facade: ChroniclerFacade,
    advisor_facade: AdvisorFacade,
) -> ToolExecutor:
    """Исполнитель со всеми навыками, собранный как в корне компоновки."""
    return build_tool_executor(
        turns_facade=turns_facade,
        diplomacy_facade=diplomacy_facade,
        gunsmith_facade=gunsmith_facade,
        game_master_facade=game_master_facade,
        chronicler_facade=chronicler_facade,
        advisor_facade=advisor_facade,
    )


# ==================================================================
# КОНТЕКСТ ИСПОЛНЕНИЯ
# ==================================================================


@pytest.fixture
def context(world: WorldState):
    """
    Фабрика контекстов сцены: по умолчанию ход державы игрока.
    """

    def _context(**overrides: Any) -> ToolExecutionContext:
        data: dict[str, Any] = {"world_state": world, "caller_faction_id": "humans"}
        data.update(overrides)
        return ToolExecutionContext(**data)

    return _context
