"""
Фасад взаимодействия с базой данных.
Адаптирует базу данных под доменный контракт SaveGameRepositoryProtocol.
"""

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.back.l01_domain.protocols.saves import SaveGameRepositoryProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.l03_infrastructure.databases.sql.management.saves import SQLSaves
from src.back.utils.logger import main_logger


class DatabaseManager(SaveGameRepositoryProtocol):
    """
    Фасад инфраструктуры баз данных.
    Имплементирует SaveGameRepositoryProtocol, преобразуя Pydantic модели в строки JSON для базы.
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
