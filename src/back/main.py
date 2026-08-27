"""
Контейнер зависимостей и провайдеры для внедрения в обработчики FastAPI.
"""

from dataclasses import dataclass
from typing import Optional

from src.back.l02_services.gameflow.facade import GameFlowFacade
from src.back.l02_services.gameflow.fsm import GameFlowFSM
from src.back.l02_services.gameflow.states import GameState
from src.back.l02_services.mechanics.chronicler.facade import ChroniclerFacade
from src.back.l02_services.mechanics.chronicler.listener import ChroniclerListener
from src.back.l02_services.mechanics.diplomacy.facade import DiplomacyFacade
from src.back.l02_services.mechanics.game_master.facade import GameMasterFacade
from src.back.l02_services.mechanics.gunsmith.facade import GunsmithFacade
from src.back.l02_services.saves.facade import SavesFacade
from src.back.l02_services.saves.loader import (
    LoadedSession,
    SessionGameDataRepository,
)  # TODO: VS Code ругается на импорт SessionGameDataRepository
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.l02_services.turns.strategic.orchestrator import StrategicTurnOrchestrator
from src.back.l02_services.turns.tactical.orchestrator import TacticalTurnOrchestrator

from src.back.l03_infrastructure.databases.manager import DatabaseManager
from src.back.l03_infrastructure.databases.sql.db import SQLDB
from src.back.l03_infrastructure.gamedata.loader import (
    StaticGameDataRegistry,
    build_static_registry,
)
from src.back.l03_infrastructure.llm.context.builder import ContextBuilder
from src.back.l03_infrastructure.llm.facade import LLMFacade
from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder

from src.back.utils.event.bus import EventBus
from src.back.utils.logger import main_logger


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
        saves_facade=saves_facade,
        gameflow_fsm=gameflow_fsm,
        gameflow_facade=gameflow_facade,
        turns_facade=turns_facade,
    )
