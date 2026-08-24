"""
Подключение к базе данных SQL.
Содержит класс SQLDB для инициализации движка (Engine) и фабрики сессий.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.back.l03_infrastructure.databases.sql.tables import Base


class SQLDB:
    """
    Управляет подключением к базе данных и выдачей асинхронных сессий.
    """

    def __init__(self, db_url: str = "sqlite+aiosqlite:///saves.db") -> None:
        self._engine = create_async_engine(db_url, echo=False)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Фабрика для получения асинхронных сессий БД."""
        return self._session_factory

    async def init_tables(self) -> None:
        """Создает таблицы в базе данных, если они еще не существуют."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        """Корректно закрывает пул соединений движка SQLAlchemy."""
        await self._engine.dispose()