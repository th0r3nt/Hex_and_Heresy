"""
Фасад, инкапсулирующий загрузку и сохранение игр.

Единая точка входа для API и конечного автомата: принимает запросы на
создание, перечисление, удаление и подъем сохранений, скрывая за собой
подготовку снимка (dumper), восстановление сессии (loader) и конкретное
хранилище (SaveGameRepositoryProtocol).
"""

from typing import Any, Optional

from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.saves import SaveGameRepositoryProtocol
from src.back.l01_domain.world.models.saves import SaveMetadata
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.saves.dumper import WorldStateDumper
from src.back.l02_services.saves.loader import (
    GameDataRepositoryFactory,
    LoadedSession,
    WorldStateLoader,
)
from src.back.utils.event.registry import GameEvents
from src.back.utils.logger import main_logger

# Слоты с фиксированными идентификаторами: перезаписываются, а не плодят записи
QUICK_SAVE_ID = "quicksave"
AUTOSAVE_ID = "autosave"


class SavesFacade:
    """
    Фасад сохранений партии.

    Право на сохранение в текущем режиме игры проверяет вызывающая сторона
    (GameFlowFacade.assert_can_save): фасад отвечает за целостность самих
    данных, а не за то, какой экран сейчас открыт.
    """

    def __init__(
        self,
        repository: SaveGameRepositoryProtocol,
        gamedata_factory: GameDataRepositoryFactory,
        dumper: Optional[WorldStateDumper] = None,
        loader: Optional[WorldStateLoader] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._repository = repository
        self._dumper = dumper or WorldStateDumper()
        self._loader = loader or WorldStateLoader(
            repository=repository, gamedata_factory=gamedata_factory
        )
        self._event_bus = event_bus

    # ==================================================================
    # СОЗДАНИЕ СОХРАНЕНИЙ
    # ==================================================================

    async def save_game(
        self,
        world_state: WorldState,
        save_name: str,
        save_id: Optional[str] = None,
    ) -> SaveMetadata:
        """
        Записывает снимок партии.

        Без save_id создается новая запись, с save_id - перезаписывается
        существующий слот. Возвращает метаданные записанного снимка.
        """
        snapshot = self._dumper.prepare(
            world_state=world_state, save_name=save_name, save_id=save_id
        )

        await self._repository.save_world_state(
            save_id=snapshot.metadata.save_id,
            save_name=snapshot.metadata.save_name,
            state=snapshot.state,
        )

        await self._publish_saved(snapshot.metadata)
        return snapshot.metadata

    async def quick_save(self, world_state: WorldState) -> SaveMetadata:
        """
        Перезаписывает слот быстрого сохранения.
        """
        return await self.save_game(
            world_state=world_state,
            save_name=self._slot_name(world_state, "Быстрое сохранение"),
            save_id=QUICK_SAVE_ID,
        )

    async def autosave(self, world_state: WorldState) -> SaveMetadata:
        """
        Перезаписывает слот автосохранения. Вызывается оркестратором ходов
        по завершении глобального такта.
        """
        return await self.save_game(
            world_state=world_state,
            save_name=self._slot_name(world_state, "Автосохранение"),
            save_id=AUTOSAVE_ID,
        )

    # ==================================================================
    # ЗАГРУЗКА И СТАРТ СЕССИИ
    # ==================================================================

    async def load_game(self, save_id: str) -> LoadedSession:
        """
        Поднимает партию из сохранения: восстанавливает WorldState и собирает
        сессионный репозиторий геймдаты, который composition root разошлет по
        сервисам активной игры.
        """
        session = await self._loader.load(save_id)

        await self._publish_loaded(save_id, session.world_state)
        main_logger.info(f"Партия из сохранения '{save_id}' восстановлена.")
        return session

    def start_session(self, world_state: WorldState) -> LoadedSession:
        """
        Готовит сессию для только что созданной партии - без обращения к базе.

        Новая игра нуждается в том же сессионном репозитории геймдаты, что и
        загруженная, поэтому сборка живет здесь, а не дублируется в стартере.
        """
        return self._loader.restore_session(world_state)

    # ==================================================================
    # ВИТРИНА СОХРАНЕНИЙ
    # ==================================================================

    async def list_saves(self) -> list[dict[str, Any]]:
        """
        Отдает список сохранений для меню загрузки (без тяжелых снимков).
        """
        return await self._repository.list_saves()

    async def has_save(self, save_id: str) -> bool:
        """
        Проверяет наличие слота - например, чтобы погасить кнопку «Продолжить».
        """
        return await self._loader.peek_metadata(save_id) is not None

    async def delete_save(self, save_id: str) -> bool:
        """
        Удаляет сохранение. Возвращает False, если записи не существовало.
        """
        return await self._repository.delete_save(save_id)

    # ==================================================================
    # СЛУЖЕБНОЕ
    # ==================================================================

    def _slot_name(self, world_state: WorldState, prefix: str) -> str:
        """
        Формирует человекочитаемое имя для перезаписываемого слота.
        """
        time = world_state.time
        return f"{prefix} - год {time.current_year}, день {time.current_day}"

    async def _publish_saved(self, metadata: SaveMetadata) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            GameEvents.GameFlow.GAME_SAVED,
            save_id=metadata.save_id,
            save_name=metadata.save_name,
            total_ticks=metadata.total_ticks,
        )

    async def _publish_loaded(self, save_id: str, world_state: WorldState) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            GameEvents.GameFlow.GAME_LOADED,
            save_id=save_id,
            world_state_id=world_state.id,
            total_ticks=world_state.time.total_ticks,
        )
