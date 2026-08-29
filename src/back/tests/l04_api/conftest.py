"""
Окружение тестов слоя доставки.

Приложение собирается здесь же и вручную: настоящий корень компоновки
поднимает базу и языковую модель, а роутерам для проверки нужны только
фасады-заглушки в app.state.container.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.gameflow.facade import GameFlowFacade
from src.back.l02_services.gameflow.fsm import GameFlowFSM
from src.back.l02_services.gameflow.states import GameState
from src.back.l02_services.mechanics.vision.facade import VisionFacade
from src.back.l02_services.saves.facade import SavesFacade
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.l02_services.world.generator import WorldGenerator
from src.back.l03_infrastructure.gamedata.loader import StaticGameDataRegistry
from src.back.l04_api.http.errors import register_exception_handlers
from src.back.l04_api.http.routers import api_router
from src.back.l04_api.ws.manager import ConnectionManager
from src.back.l04_api.ws.router import router as ws_router


# ==================================================================
# ЗАГЛУШКА КОНТЕЙНЕРА
# ==================================================================


@dataclass
class FakeContainer:
    """
    Минимальный контейнер: только то, что спрашивают роутеры.

    Повторяет контракт AppContainer (в том числе bind_session), но ничего
    не поднимает - фасады подкладываются тестом поштучно.
    """

    gameflow_facade: Any = None
    turns_facade: Any = None
    saves_facade: Any = None
    diplomacy_facade: Any = None
    gunsmith_facade: Any = None
    game_master_facade: Any = None
    chronicler_facade: Any = None
    advisor_facade: Any = None
    llm_facade: Any = None
    event_bus: Any = None
    world_generator: Any = None

    bound_sessions: list[Any] = field(default_factory=list)

    def bind_session(self, session: Any) -> None:
        self.bound_sessions.append(session)
        self.gameflow_facade.bind_world_state(session.world_state)

    def unbind_session(self) -> None:
        self.gameflow_facade.unbind_world_state()


# ==================================================================
# ФИКСТУРЫ
# ==================================================================


@pytest.fixture
def container(static_registry: StaticGameDataRegistry) -> FakeContainer:
    """
    Контейнер с настоящим игровым потоком: его переходы тесты проверяют.

    Генератор мира, сессии и туман войны тоже настоящие - без них эндпоинт
    старта новой партии проверять нечем.
    """
    vision_facade = VisionFacade()
    world_generator = WorldGenerator(
        gamedata=static_registry, vision_facade=vision_facade
    )

    return FakeContainer(
        gameflow_facade=GameFlowFacade(world_generator=world_generator),
        saves_facade=SavesFacade(
            repository=EmptySaveRepository(),
            gamedata_factory=lambda custom_equipment: static_registry,
        ),
        turns_facade=TurnsFacade(vision_facade=vision_facade, gamedata=static_registry),
        world_generator=world_generator,
    )


@pytest.fixture
def app(container: FakeContainer) -> FastAPI:
    """
    Приложение, собранное так же, как это предстоит делать main.py.
    """
    application = FastAPI()
    application.include_router(api_router)
    application.include_router(ws_router)
    register_exception_handlers(application)

    application.state.container = container
    application.state.ws_manager = ConnectionManager()

    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def world_state() -> WorldState:
    return WorldState()


@pytest.fixture
def active_party(container: FakeContainer, world_state: WorldState) -> WorldState:
    """
    Идущая партия: игра на глобальной карте, мир привязан к потоку.
    """
    container.gameflow_facade = GameFlowFacade(
        fsm=GameFlowFSM(initial_state=GameState.STRATEGIC_MAP)
    )
    container.gameflow_facade.bind_world_state(world_state)
    return world_state


# ==================================================================
# ВСПОМОГАТЕЛЬНОЕ
# ==================================================================


class EmptySaveRepository:
    """
    Хранилище сохранений-пустышка: старту новой партии база не нужна, но
    фасад сохранений собирает загрузчик поверх какого-то репозитория.
    """

    async def save_world_state(
        self, save_id: str, save_name: str, state: WorldState
    ) -> None:
        return None

    async def load_world_state(self, save_id: str) -> Optional[WorldState]:
        return None

    async def list_saves(self) -> list[dict[str, Any]]:
        return []

    async def delete_save(self, save_id: str) -> bool:
        return False


class FakeSession:
    """Подобие LoadedSession: роутеру загрузки нужен только мир."""

    def __init__(self, world_state: WorldState) -> None:
        self.world_state = world_state
        self.gamedata: Optional[Any] = None
