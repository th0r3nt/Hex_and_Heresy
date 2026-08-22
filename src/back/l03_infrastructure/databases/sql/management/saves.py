"""
Глупые CRUD-операции с таблицей сохранений.
Изолирует синтаксис SQLAlchemy от остальной инфраструктуры.
"""

from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.back.l03_infrastructure.databases.sql.tables import SaveGameTable


class SQLSaves:
    """
    Инкапсулирует SQL-запросы к таблице `saves`.
    Все методы принимают `AsyncSession`, оставляя управление транзакциями на совести вызывающего фасада.
    """

    @staticmethod
    async def create_or_update(
        session: AsyncSession, save_id: str, name: str, data: str
    ) -> None:
        """Создает новое сохранение или обновляет существующее по ID."""
        stmt = select(SaveGameTable).where(SaveGameTable.id == save_id)
        result = await session.execute(stmt)
        save_record = result.scalar_one_or_none()

        if save_record is None:
            save_record = SaveGameTable(
                id=save_id, name=name, data=data, created_at=datetime.now(timezone.utc)
            )
            session.add(save_record)
        else:
            save_record.name = name
            save_record.data = data
            save_record.created_at = datetime.now(timezone.utc)

    @staticmethod
    async def get_by_id(session: AsyncSession, save_id: str) -> Optional[SaveGameTable]:
        """Получает запись сохранения по ID."""
        stmt = select(SaveGameTable).where(SaveGameTable.id == save_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(session: AsyncSession) -> Sequence[SaveGameTable]:
        """Возвращает все сохранения, отсортированные от новых к старым."""
        stmt = select(SaveGameTable).order_by(SaveGameTable.created_at.desc())
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def delete(session: AsyncSession, save_id: str) -> bool:
        """Удаляет сохранение по ID. Возвращает True, если запись существовала."""
        stmt = delete(SaveGameTable).where(SaveGameTable.id == save_id)
        result = await session.execute(stmt)
        return result.rowcount > 0
