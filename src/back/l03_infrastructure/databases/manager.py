"""
Фасад взаимодействия с базой данных.
Адаптирует базу данных под доменные контракты SaveGameRepositoryProtocol
и ChroniclerRepositoryProtocol.
"""

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.back.l01_domain.protocols.chronicler import ChroniclerRepositoryProtocol
from src.back.l01_domain.protocols.saves import SaveGameRepositoryProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.l03_infrastructure.databases.sql.management.chronicles import SQLChronicles
from src.back.l03_infrastructure.databases.sql.management.saves import SQLSaves
from src.back.utils.logger import main_logger


class DatabaseManager(SaveGameRepositoryProtocol, ChroniclerRepositoryProtocol):
    """
    Фасад инфраструктуры баз данных.
    Имплементирует SaveGameRepositoryProtocol, преобразуя Pydantic модели в строки JSON для базы,
    и ChroniclerRepositoryProtocol - для летописи и Зала павших, которые переживают партию.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save_world_state(self, save_id: str, save_name: str, state: WorldState) -> None:
        """Сериализует WorldState и сохраняет его в БД."""
        # Превращает все армии, отряды и фракции в одну огромную JSON-строку
        raw_json = state.model_dump_json()

        try:
            async with self._session_factory() as session:
                async with session.begin():  # Управляем транзакцией
                    await SQLSaves.create_or_update(session, save_id, save_name, raw_json)
            main_logger.info(f"Игра успешно сохранена: '{save_name}' (ID: {save_id}).")
        except Exception as e:
            main_logger.error(f"Ошибка при сохранении игры '{save_name}': {e}")
            raise

    async def load_world_state(self, save_id: str) -> Optional[WorldState]:
        """Загружает JSON из БД и восстанавливает Pydantic-дерево WorldState."""
        try:
            async with self._session_factory() as session:
                record = await SQLSaves.get_by_id(session, save_id)
                if record is None:
                    main_logger.warning(f"Сохранение с ID '{save_id}' не найдено.")
                    return None

                # Валидирует сырой JSON и восстанавливает все типы данных
                state = WorldState.model_validate_json(record.data)
                main_logger.info(f"Игра (ID: {save_id}) успешно загружена.")
                return state
        except Exception as e:
            main_logger.error(f"Ошибка при загрузке сохранения ID {save_id}: {e}")
            raise

    async def list_saves(self) -> list[dict[str, Any]]:
        """Отдает список метаданных сохранений (без тяжелого поля data)."""
        try:
            async with self._session_factory() as session:
                records = await SQLSaves.list_all(session)
                return [
                    {"id": r.id, "name": r.name, "created_at": r.created_at.isoformat()}
                    for r in records
                ]
        except Exception as e:
            main_logger.error(f"Ошибка при получении списка сохранений: {e}")
            return []

    async def delete_save(self, save_id: str) -> bool:
        """Удаляет сохранение из базы."""
        try:
            async with self._session_factory() as session:
                async with session.begin():
                    success = await SQLSaves.delete(session, save_id)
                    if success:
                        main_logger.info(f"Сохранение (ID: {save_id}) успешно удалено.")
                    else:
                        main_logger.warning(
                            f"Попытка удалить несуществующее сохранение (ID: {save_id})."
                        )
                    return success
        except Exception as e:
            main_logger.error(f"Ошибка при удалении сохранения ID {save_id}: {e}")
            return False

    # ==================================================================
    # ЛЕТОПИСЬ И ЗАЛ ПАВШИХ
    # ==================================================================

    async def record_battle_history(
        self,
        battle_id: str,
        title: str,
        quote: str,
        body: str,
        tick: int,
        location_name: str,
    ) -> None:
        """
        Записывает страницу летописи о бое. Повторная запись об одном бое
        игнорируется: летописец мог перегенерировать текст.
        """
        try:
            async with self._session_factory() as session:
                async with session.begin():
                    existing = await SQLChronicles.get_battle_entry(session, battle_id)
                    if existing is not None:
                        main_logger.debug(
                            f"Летопись боя '{battle_id}' уже записана, пропуск."
                        )
                        return

                    await SQLChronicles.create_battle_entry(
                        session,
                        battle_id=battle_id,
                        title=title,
                        quote=quote,
                        body=body,
                        tick=tick,
                        location_name=location_name,
                    )
            main_logger.info(f"Летопись боя '{battle_id}' записана: «{title}».")
        except Exception as e:
            main_logger.error(f"Ошибка при записи летописи боя '{battle_id}': {e}")
            raise

    async def record_fallen_squad(
        self,
        squad_name: str,
        commander_name: str,
        race_id: str,
        biography: str,
        death_tick: int,
        killer_name: str,
    ) -> None:
        """
        Ставит надгробие в Зале павших. Один и тот же отряд на одном такте
        хоронят единожды.
        """
        try:
            async with self._session_factory() as session:
                async with session.begin():
                    existing = await SQLChronicles.get_fallen_record(
                        session, squad_name, death_tick
                    )
                    if existing is not None:
                        main_logger.debug(
                            f"Надгробие '{squad_name}' (такт {death_tick}) уже стоит, пропуск."
                        )
                        return

                    await SQLChronicles.create_fallen_record(
                        session,
                        squad_name=squad_name,
                        commander_name=commander_name,
                        race_id=race_id,
                        biography=biography,
                        death_tick=death_tick,
                        killer_name=killer_name,
                    )
            main_logger.info(f"В Зал павших записан отряд '{squad_name}'.")
        except Exception as e:
            main_logger.error(f"Ошибка при записи павшего отряда '{squad_name}': {e}")
            raise

    async def get_history_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        """Страницы летописи для вкладки книги."""
        try:
            async with self._session_factory() as session:
                records = await SQLChronicles.list_battle_entries(session, limit=limit)
                return [
                    {
                        "id": r.id,
                        "battle_id": r.battle_id,
                        "title": r.title,
                        "quote": r.quote,
                        "body": r.body,
                        "tick": r.tick,
                        "location_name": r.location_name,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in records
                ]
        except Exception as e:
            main_logger.error(f"Ошибка при чтении летописи: {e}")
            return []

    async def get_fallen_records(self, limit: int = 50) -> list[dict[str, Any]]:
        """Надгробия для вкладки «Зал павших»."""
        try:
            async with self._session_factory() as session:
                records = await SQLChronicles.list_fallen_records(session, limit=limit)
                return [
                    {
                        "id": r.id,
                        "squad_name": r.squad_name,
                        "commander_name": r.commander_name,
                        "race_id": r.race_id,
                        "biography": r.biography,
                        "death_tick": r.death_tick,
                        "killer_name": r.killer_name,
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in records
                ]
        except Exception as e:
            main_logger.error(f"Ошибка при чтении Зала павших: {e}")
            return []
