"""
Глупые CRUD-операции с таблицами летописи и Зала павших.
Изолирует синтаксис SQLAlchemy от остальной инфраструктуры.
"""

from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.back.l03_infrastructure.databases.sql.tables import (
    ChronicleEntryTable,
    FallenRecordTable,
)


class SQLChronicles:
    """
    Инкапсулирует SQL-запросы к таблицам `chronicle_entries` и `fallen_records`.
    Все методы принимают `AsyncSession`, оставляя управление транзакциями на
    совести вызывающего фасада.
    """

    # ==================================================================
    # ЛЕТОПИСЬ СРАЖЕНИЙ
    # ==================================================================

    @staticmethod
    async def create_battle_entry(
        session: AsyncSession,
        battle_id: str,
        title: str,
        quote: str,
        body: str,
        tick: int,
        location_name: str,
    ) -> ChronicleEntryTable:
        """
        Записывает страницу летописи о бое.
        """
        entry = ChronicleEntryTable(
            id=str(uuid4()),
            battle_id=battle_id,
            title=title,
            quote=quote,
            body=body,
            tick=tick,
            location_name=location_name,
            created_at=datetime.now(timezone.utc),
        )
        session.add(entry)
        return entry

    @staticmethod
    async def get_battle_entry(
        session: AsyncSession, battle_id: str
    ) -> Optional[ChronicleEntryTable]:
        """
        Страница о конкретном бое, если о нем уже писали.
        """
        stmt = select(ChronicleEntryTable).where(ChronicleEntryTable.battle_id == battle_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def list_battle_entries(
        session: AsyncSession, limit: int = 50
    ) -> Sequence[ChronicleEntryTable]:
        """
        Страницы летописи от свежих к старым.
        """
        stmt = (
            select(ChronicleEntryTable)
            .order_by(ChronicleEntryTable.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    # ==================================================================
    # ЗАЛ ПАВШИХ
    # ==================================================================

    @staticmethod
    async def create_fallen_record(
        session: AsyncSession,
        squad_name: str,
        commander_name: str,
        race_id: str,
        biography: str,
        death_tick: int,
        killer_name: str,
    ) -> FallenRecordTable:
        """
        Ставит надгробие в Зале павших.
        """
        record = FallenRecordTable(
            id=str(uuid4()),
            squad_name=squad_name,
            commander_name=commander_name,
            race_id=race_id,
            biography=biography,
            death_tick=death_tick,
            killer_name=killer_name,
            created_at=datetime.now(timezone.utc),
        )
        session.add(record)
        return record

    @staticmethod
    async def get_fallen_record(
        session: AsyncSession, squad_name: str, death_tick: int
    ) -> Optional[FallenRecordTable]:
        """
        Надгробие конкретного отряда.

        Ключ - имя и такт гибели: одно и то же имя может носить отряд другой
        партии, но дважды погибнуть на одном такте он не может.
        """
        stmt = select(FallenRecordTable).where(
            FallenRecordTable.squad_name == squad_name,
            FallenRecordTable.death_tick == death_tick,
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def list_fallen_records(
        session: AsyncSession, limit: int = 50
    ) -> Sequence[FallenRecordTable]:
        """
        Надгробия от свежих к старым.
        """
        stmt = (
            select(FallenRecordTable)
            .order_by(FallenRecordTable.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
