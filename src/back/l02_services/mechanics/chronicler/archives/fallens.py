"""
Логика механики "Зал павших" (некрологи ветеранов и героев).

Безымянное ополчение хоронят общими словами в летописи боя. Сюда попадают
только те, у кого было имя: именные отряды и герои. Их надгробия переживают
партию - игрок открывает Зал павших на сотом такте и перечитывает эпитафии.
"""

from typing import Any, Optional

from src.back.l01_domain.protocols.chronicler import ChroniclerRepositoryProtocol
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.constants import CHRONICLE_HISTORY_PAGE_SIZE
from src.back.l01_domain.world.models.chronicle import FallenRecord
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.event.registry import GameEvents
from src.back.utils.logger import main_logger


class HallOfFallen:
    """
    Ведет Зал павших: ставит надгробия и отдает их интерфейсу.
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

    async def bury(self, world_state: WorldState, record: FallenRecord) -> bool:
        """
        Ставит надгробие. Возвращает False, если этого павшего уже похоронили.
        """
        if self.is_buried(world_state, record.squad_id):
            return False

        world_state.add_fallen_record(record)
        await self._persist(record)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Chronicler.FALLEN_RECORDED,
                record_id=record.id,
                squad_id=record.squad_id,
                squad_name=record.squad_name,
                faction_id=record.faction_id,
                death_tick=record.death_tick,
            )

        return True

    # ==================================================================
    # ВИТРИНА
    # ==================================================================

    def is_buried(self, world_state: WorldState, squad_id: str) -> bool:
        return any(record.squad_id == squad_id for record in world_state.fallen_records)

    def get_records(
        self, world_state: WorldState, limit: int = CHRONICLE_HISTORY_PAGE_SIZE
    ) -> list[FallenRecord]:
        """
        Надгробия от свежих к старым.
        """
        return list(reversed(world_state.fallen_records))[:limit]

    async def get_persisted_records(
        self, limit: int = CHRONICLE_HISTORY_PAGE_SIZE
    ) -> list[dict[str, Any]]:
        """
        Павшие всех прошлых партий из базы.
        """
        if self._repository is None:
            return []
        return await self._repository.get_fallen_records(limit=limit)

    # ==================================================================
    # СЛУЖЕБНОЕ
    # ==================================================================

    async def _persist(self, record: FallenRecord) -> None:
        """
        Пишет надгробие в базу. Сбой хранилища не отменяет похорон: запись
        уже лежит в WorldState.
        """
        if self._repository is None:
            return

        try:
            await self._repository.record_fallen_squad(
                squad_name=record.squad_name,
                commander_name=record.commander_name or "",
                race_id=record.race.value,
                biography=record.epitaph,
                death_tick=record.death_tick,
                killer_name=record.killer_name,
            )
        except Exception as error:
            main_logger.error(
                f"[Chronicler] Надгробие '{record.squad_name}' не записано в базу: {error}"
            )
