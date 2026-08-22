"""
Описание структур SQL-таблиц (схемы базы данных).
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""

    pass


class SaveGameTable(Base):
    """
    Таблица для хранения сохранений игр.
    Хранит метаданные для списков в меню и сырой JSON `WorldState` для восстановления.
    """

    __tablename__ = "saves"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, description="UUID сохранения"
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, description="Пользовательское имя сейва"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        description="Дата и время создания",
    )

    # Колонка Text может вмещать огромные JSON-строки, что нам и нужно для WorldState
    data: Mapped[str] = mapped_column(Text, nullable=False, description="JSON WorldState")
