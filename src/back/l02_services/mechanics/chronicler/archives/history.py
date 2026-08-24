"""
Хронология битв, событий и слухов, записанных летописцем.

Летопись живет в двух местах сразу: в WorldState - чтобы уехать в сохранение
вместе с партией, и в базе данных - чтобы пережить саму партию. Репозиторий
необязателен: без него летопись просто не переживет выход из игры, но
механика работает.
"""

from typing import Any, Optional

from src.back.l01_domain.protocols.chronicler import ChroniclerRepositoryProtocol
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.constants import CHRONICLE_HISTORY_PAGE_SIZE
from src.back.l01_domain.world.models.chronicle import ChronicleEntry, RumorEntry
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.event.registry import GameEvents
from src.back.utils.logger import main_logger


class ChronicleArchive:
    """
    Ведет хронологию сражений и слухов текущей партии.
    """

    def __init__(
        self,
        repository: Optional[ChroniclerRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._repository = repository
        self._event_bus = event_bus

    # ==================================================================
    # ЗАПИСЬ
    # ==================================================================

    async def record_battle(self, world_state: WorldState, entry: ChronicleEntry) -> bool:
        """
        Дописывает страницу летописи о бое.

        Возвращает False, если о бое уже писали: перегенерация текста не
        должна плодить свитки об одном сражении.
        """
        if self.has_entry(world_state, entry.battle_id):
            return False

        world_state.add_chronicle_entry(entry)
        await self._persist_battle(entry)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Chronicler.BATTLE_RECORDED,
                battle_id=entry.battle_id,
                entry_id=entry.id,
                title=entry.title,
                tick=entry.tick,
                faction_id=entry.faction_id,
            )

        return True

    async def record_rumor(self, world_state: WorldState, rumor: RumorEntry) -> None:
        """
        Кладет слух в окно логов. В базу слухи не идут: это шум эпохи,
        который живет ровно столько, сколько сама партия.
        """
        world_state.add_rumor(rumor)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Chronicler.RUMOR_GENERATED,
                rumor_id=rumor.id,
                text=rumor.text,
                tick=rumor.tick,
                faction_id=rumor.faction_id,
            )

    # ==================================================================
    # ВИТРИНА
    # ==================================================================

    def has_entry(self, world_state: WorldState, battle_id: str) -> bool:
        return any(entry.battle_id == battle_id for entry in world_state.chronicle_entries)

    def get_entries(
        self, world_state: WorldState, limit: int = CHRONICLE_HISTORY_PAGE_SIZE
    ) -> list[ChronicleEntry]:
        """
        Отдает страницы летописи от свежих к старым - в том порядке, в каком
        их листает игрок.
        """
        return list(reversed(world_state.chronicle_entries))[:limit]

    def get_rumors(
        self, world_state: WorldState, limit: int = CHRONICLE_HISTORY_PAGE_SIZE
    ) -> list[RumorEntry]:
        return list(reversed(world_state.rumors))[:limit]

    async def get_persisted_entries(
        self, limit: int = CHRONICLE_HISTORY_PAGE_SIZE
    ) -> list[dict[str, Any]]:
        """
        Летописи всех прошлых партий из базы - для меню вне активной игры.
        """
        if self._repository is None:
            return []
        return await self._repository.get_history_entries(limit=limit)

    # ==================================================================
    # СЛУЖЕБНОЕ
    # ==================================================================

    async def _persist_battle(self, entry: ChronicleEntry) -> None:
        """
        Пишет страницу в базу. Сбой хранилища не отменяет саму летопись:
        она уже лежит в WorldState и уедет в ближайшее сохранение.
        """
        if self._repository is None:
            return

        try:
            await self._repository.record_battle_history(
                battle_id=entry.battle_id,
                title=entry.title,
                quote=entry.quote,
                body=entry.body,
                tick=entry.tick,
                location_name=entry.location_name,
            )
        except Exception as error:
            main_logger.error(
                f"[Chronicler] Летопись боя '{entry.battle_id}' не записана в базу: {error}"
            )
