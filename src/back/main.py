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
from src.back.l02_services.saves.facade import SavesFacade
from src.back.l02_services.saves.loader import LoadedSession
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.l02_services.turns.strategic.orchestrator import StrategicTurnOrchestrator
from src.back.l02_services.turns.tactical.orchestrator import TacticalTurnOrchestrator

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

from src.back.utils.event.bus import EventBus
from src.back.utils.logger import main_logger

# Клиент игры - окно Electron, которое открывает страницу с диска и потому
# приходит с "чужим" источником. Сервер слушает только петлю, так что
# разрешать ему любые источники безопасно.
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
    gameflow_fsm: GameFlowFSM
    gameflow_facade: GameFlowFacade
    turns_facade: TurnsFacade

    # ==================================================================
    # Активная партия
    # ==================================================================

    def bind_session(self, session: LoadedSession) -> None:
        """
        Рассылает мир начатой или загруженной партии по сервисам, которые
        держат его у себя между запросами.

        Знать полный список таких сервисов может только корень компоновки,
        поэтому рассылка живет здесь, а не в роутере загрузки.
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
# ГЛАВНАЯ СБОРКА КОНТЕЙНЕРА ЗАВИСИМОСТЕЙ
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
    gameflow_fsm = GameFlowFSM(
        initial_state=GameState.MAIN_MENU,
        event_bus=event_bus,
    )
    gameflow_facade = GameFlowFacade(
        fsm=gameflow_fsm,
        event_bus=event_bus,
    )

    # 4. Оркестрация ходов
    strategic_orchestrator = StrategicTurnOrchestrator(
        diplomacy_facade=diplomacy_facade,
        gamedata=registry,
        event_bus=event_bus,
    )
    tactical_orchestrator = TacticalTurnOrchestrator(
        event_bus=event_bus,
    )
    turns_facade = TurnsFacade(
        strategic_orchestrator=strategic_orchestrator,
        tactical_orchestrator=tactical_orchestrator,
        event_bus=event_bus,
    )

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
        gameflow_fsm=gameflow_fsm,
        gameflow_facade=gameflow_facade,
        turns_facade=turns_facade,
    )


# =======================================================================
# ЖИЗНЕННЫЙ ЦИКЛ ПРИЛОЖЕНИЯ
# =======================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Асинхронная часть старта и остановки сервера.

    Все, что требует живого цикла событий, живет здесь, а не в create_app():
    таблицы базы создаются при старте, а фоновые публикации шины и сетевые
    клиенты моделей аккуратно доигрываются и закрываются при остановке.
    """
    container: AppContainer = app.state.container
    dispatcher: EventDispatcher = app.state.ws_dispatcher

    main_logger.info("[APP] Запуск приложения...")

    # Схема базы сохранений создается на месте: отдельных миграций у
    # локального десктопного приложения нет.
    await container.db.init_tables()

    # Мост "шина событий -> сокет" подписывается только на живом приложении,
    # чтобы при остановке гарантированно отписаться.
    dispatcher.register(container.event_bus)

    main_logger.info("[APP] Приложение готово к работе.")

    try:
        yield
    finally:
        main_logger.info("[APP] Остановка приложения...")

        dispatcher.unregister(container.event_bus)

        # Порядок обратный использованию: сначала дожидаемся фоновых
        # слушателей (они ходят в модели), потом закрываем клиентов моделей
        # и лишь затем гасим пул соединений с базой.
        await container.event_bus.stop()
        await container.llm_facade.close_all()
        await container.db.dispose()

        main_logger.info("[APP] Приложение остановлено.")


# =======================================================================
# СБОРКА ПРИЛОЖЕНИЯ FASTAPI
# =======================================================================


def create_app(container: Optional[AppContainer] = None) -> FastAPI:
    """
    Собирает приложение FastAPI поверх контейнера зависимостей.

    Готовый контейнер можно передать снаружи (тесты, отдельные сценарии
    запуска) - иначе он собирается здесь же настройками по умолчанию.
    """
    app = FastAPI(
        title="Hex & Heresy",
        description="Бэкенд: игровые команды по HTTP и лента событий мира по WebSocket.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 1. Зависимости. Роутеры достают их из app.state через dependencies.py
    app.state.container = container or create_app_container()
    app.state.ws_manager = ConnectionManager()
    app.state.ws_dispatcher = EventDispatcher(manager=app.state.ws_manager)

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

    # 4. Перевод доменных ошибок в статусы HTTP
    register_exception_handlers(app)

    return app


# =======================================================================
# ТОЧКА ВХОДА
# =======================================================================


if __name__ == "__main__":
    import uvicorn

    # Фабрика, а не готовый объект: контейнер собирается один раз, уже внутри
    # процесса сервера.
    uvicorn.run(
        "src.back.main:create_app",
        factory=True,
        host=SERVER_HOST,
        port=SERVER_PORT,
    )
