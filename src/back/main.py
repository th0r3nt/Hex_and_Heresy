"""
Корень компоновки (Composition Root) игры.

Здесь собирается граф зависимостей (AppContainer) и на его основе -
приложение FastAPI: роутеры, обработчики доменных ошибок и канал
уведомлений. Логики игры в этом модуле нет, только сборка.

Запуск сервера:
    python -m src.back.main
    uvicorn src.back.main:create_app --factory
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.back.l02_services.gameflow.facade import GameFlowFacade
from src.back.l02_services.gameflow.fsm import GameFlowFSM
from src.back.l02_services.gameflow.states import GameState
from src.back.l02_services.mechanics.advisor.facade import AdvisorFacade
from src.back.l02_services.mechanics.chronicler.facade import ChroniclerFacade
from src.back.l02_services.mechanics.chronicler.listener import ChroniclerListener
from src.back.l02_services.mechanics.diplomacy.facade import DiplomacyFacade
from src.back.l02_services.mechanics.game_master.facade import GameMasterFacade
from src.back.l02_services.mechanics.gunsmith.facade import GunsmithFacade
from src.back.l02_services.mechanics.settlements.facade import SettlementsFacade
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.l02_services.mechanics.tools.factory import build_tool_executor
from src.back.l02_services.mechanics.victory.facade import VictoryFacade
from src.back.l02_services.mechanics.vision.facade import VisionFacade
from src.back.l02_services.saves.facade import SavesFacade
from src.back.l02_services.saves.loader import LoadedSession
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.l02_services.turns.strategic.orchestrator import StrategicTurnOrchestrator
from src.back.l02_services.turns.tactical.orchestrator import TacticalTurnOrchestrator
from src.back.l02_services.world.generator import WorldGenerator

from src.back.l03_infrastructure.databases.manager import DatabaseManager
from src.back.l03_infrastructure.databases.sql.db import SQLDB
from src.back.l03_infrastructure.gamedata.loader import (
    SessionGameDataRepository,
    StaticGameDataRegistry,
    build_static_registry,
)
from src.back.l03_infrastructure.llm.context.builder import ContextBuilder
from src.back.l03_infrastructure.llm.facade import LLMFacade
from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder

from src.back.l04_api.http.errors import register_exception_handlers
from src.back.l04_api.http.routers import api_router
from src.back.l04_api.ws.dispatcher import EventDispatcher
from src.back.l04_api.ws.manager import ConnectionManager
from src.back.l04_api.ws.router import router as ws_router
from src.back.l04_api.ws.visibility import PlayerVisionGate

from src.back.utils.event.bus import EventBus
from src.back.utils.logger import main_logger

ALLOWED_ORIGINS = ["*"]

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000


@dataclass
class AppContainer:
    """
    Контейнер экземпляров инфраструктуры и прикладных сервисов.
    Хранится в состоянии приложения FastAPI (app.state.container).
    """

    # Инфраструктура
    db: SQLDB
    db_manager: DatabaseManager
    static_registry: StaticGameDataRegistry
    event_bus: EventBus
    prompt_builder: PromptBuilder
    context_builder: ContextBuilder
    llm_facade: LLMFacade

    # Сервисы и фасады
    chronicler_facade: ChroniclerFacade
    chronicler_listener: ChroniclerListener
    advisor_facade: AdvisorFacade
    diplomacy_facade: DiplomacyFacade
    gunsmith_facade: GunsmithFacade
    game_master_facade: GameMasterFacade
    saves_facade: SavesFacade
    victory_facade: VictoryFacade
    vision_facade: VisionFacade
    settlements_facade: SettlementsFacade
    world_generator: WorldGenerator
    gameflow_fsm: GameFlowFSM
    gameflow_facade: GameFlowFacade
    turns_facade: TurnsFacade
    tool_executor: ToolExecutor

    # ==================================================================
    # Активная партия
    # ==================================================================

    def bind_session(self, session: LoadedSession) -> None:
        """
        Рассылает мир начатой или загруженной партии по сервисам.
        """
        self.gameflow_facade.bind_world_state(session.world_state)
        self.chronicler_listener.bind_world_state(session.world_state)

    def unbind_session(self) -> None:
        """
        Отвязывает партию при выходе в главное меню.
        """
        self.gameflow_facade.unbind_world_state()
        self.advisor_facade.forget_proposals()


# =======================================================================
# Главная сборка контейнера зависимостей
# =======================================================================


def create_app_container(
    db_url: str = "sqlite+aiosqlite:///saves.db",
    static_registry: Optional[StaticGameDataRegistry] = None,
) -> AppContainer:
    """
    Выполняет полную сборку графа зависимостей (Composition Root).
    """
    main_logger.info("Начало сборки контейнера зависимостей...")

    # 1. Инфраструктурный слой
    db = SQLDB(db_url=db_url)
    db_manager = DatabaseManager(session_factory=db.session_factory)
    registry = static_registry or build_static_registry()
    event_bus = EventBus()
    prompt_builder = PromptBuilder()
    context_builder = ContextBuilder()
    llm_facade = LLMFacade()

    # 2. Фасады механик
    chronicler_facade = ChroniclerFacade(
        llm_client=llm_facade,
        repository=db_manager,
        event_bus=event_bus,
        prompt_builder=prompt_builder,
        context_builder=context_builder,
    )
    chronicler_listener = ChroniclerListener(
        facade=chronicler_facade,
        run_in_background=True,
    )
    chronicler_listener.register(event_bus)

    diplomacy_facade = DiplomacyFacade(
        llm_client=llm_facade,
        prompt_builder=prompt_builder,
        context_builder=context_builder,
        event_bus=event_bus,
    )

    gunsmith_facade = GunsmithFacade(
        llm_client=llm_facade,
        prompt_builder=prompt_builder,
        context_builder=context_builder,
        event_bus=event_bus,
    )

    advisor_facade = AdvisorFacade(
        llm_client=llm_facade,
        prompt_builder=prompt_builder,
        context_builder=context_builder,
        event_bus=event_bus,
    )

    game_master_facade = GameMasterFacade(
        llm_client=llm_facade,
        prompt_builder=prompt_builder,
        context_builder=context_builder,
        gamedata_repository=registry,
        event_bus=event_bus,
    )

    saves_facade = SavesFacade(
        repository=db_manager,
        gamedata_factory=lambda custom_eq: SessionGameDataRepository(
            static_registry=registry,
            custom_equipment=custom_eq,
        ),
        event_bus=event_bus,
    )

    # 3. Игровой поток и конечный автомат
    victory_facade = VictoryFacade(event_bus=event_bus)
    vision_facade = VisionFacade(event_bus=event_bus)
    settlements_facade = SettlementsFacade(event_bus=event_bus)

    world_generator = WorldGenerator(
        gamedata=registry,
        vision_facade=vision_facade,
        event_bus=event_bus,
    )

    gameflow_fsm = GameFlowFSM(
        initial_state=GameState.MAIN_MENU,
        event_bus=event_bus,
    )
    gameflow_facade = GameFlowFacade(
        fsm=gameflow_fsm,
        event_bus=event_bus,
        victory_facade=victory_facade,
        world_generator=world_generator,
    )

    # 4. Оркестрация ходов
    strategic_orchestrator = StrategicTurnOrchestrator(
        diplomacy_facade=diplomacy_facade,
        victory_facade=victory_facade,
        vision_facade=vision_facade,
        settlements_facade=settlements_facade,
        gameflow_facade=gameflow_facade,
        gamedata=registry,
        event_bus=event_bus,
    )
    tactical_orchestrator = TacticalTurnOrchestrator(
        event_bus=event_bus,
    )
    turns_facade = TurnsFacade(
        strategic_orchestrator=strategic_orchestrator,
        tactical_orchestrator=tactical_orchestrator,
        victory_facade=victory_facade,
        vision_facade=vision_facade,
        event_bus=event_bus,
    )

    # 5. Диспетчер инструментов (Function Calling)
    tool_executor = build_tool_executor(
        turns_facade=turns_facade,
        diplomacy_facade=diplomacy_facade,
        gunsmith_facade=gunsmith_facade,
        game_master_facade=game_master_facade,
        chronicler_facade=chronicler_facade,
        advisor_facade=advisor_facade,
    )

    # Позднее связывание исполнителя с фасадами
    advisor_facade.set_tool_executor(tool_executor)
    if diplomacy_facade._negotiations is not None:
        diplomacy_facade._negotiations.set_tool_executor(tool_executor)

    main_logger.info("Контейнер зависимостей успешно собран.")

    return AppContainer(
        db=db,
        db_manager=db_manager,
        static_registry=registry,
        event_bus=event_bus,
        prompt_builder=prompt_builder,
        context_builder=context_builder,
        llm_facade=llm_facade,
        chronicler_facade=chronicler_facade,
        chronicler_listener=chronicler_listener,
        diplomacy_facade=diplomacy_facade,
        gunsmith_facade=gunsmith_facade,
        game_master_facade=game_master_facade,
        advisor_facade=advisor_facade,
        saves_facade=saves_facade,
        victory_facade=victory_facade,
        vision_facade=vision_facade,
        settlements_facade=settlements_facade,
        world_generator=world_generator,
        gameflow_fsm=gameflow_fsm,
        gameflow_facade=gameflow_facade,
        turns_facade=turns_facade,
        tool_executor=tool_executor,
    )


# =======================================================================
# Жизненный цикл приложения
# =======================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: AppContainer = app.state.container
    dispatcher: EventDispatcher = app.state.ws_dispatcher

    main_logger.info("[APP] Запуск приложения...")

    await container.db.init_tables()
    dispatcher.register(container.event_bus)

    main_logger.info("[APP] Приложение готово к работе.")

    try:
        yield
    finally:
        main_logger.info("[APP] Остановка приложения...")

        dispatcher.unregister(container.event_bus)
        await container.event_bus.stop()
        await container.llm_facade.close_all()
        await container.db.dispose()

        main_logger.info("[APP] Приложение остановлено.")


# =======================================================================
# Сборка приложения FastAPI
# =======================================================================


def create_app(container: Optional[AppContainer] = None) -> FastAPI:
    app = FastAPI(
        title="Hex & Heresy",
        description="Бэкенд: игровые команды по HTTP и лента событий мира по WebSocket.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.container = container or create_app_container()
    app.state.ws_manager = ConnectionManager()

    resolved_container = app.state.container
    app.state.ws_dispatcher = EventDispatcher(
        manager=app.state.ws_manager,
        visibility_gate=PlayerVisionGate(
            gameflow_facade=resolved_container.gameflow_facade,
            vision_facade=resolved_container.vision_facade,
        ),
    )

    # 2. Доступ клиента к серверу
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Транспорт: команды игрока и канал уведомлений
    app.include_router(api_router)
    app.include_router(ws_router)

    register_exception_handlers(app)

    return app


# =======================================================================
# ТОЧКА ВХОДА
# =======================================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.back.main:create_app",
        factory=True,
        host=SERVER_HOST,
        port=SERVER_PORT,
    )
