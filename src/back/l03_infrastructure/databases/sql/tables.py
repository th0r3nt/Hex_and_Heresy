"""
Описание структур SQL-таблиц (схемы базы данных).
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
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
        String(36), primary_key=True, comment="UUID сохранения"
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Пользовательское имя сейва"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        comment="Дата и время создания",
    )

    # Колонка Text может вмещать огромные JSON-строки, что нам и нужно для WorldState
    data: Mapped[str] = mapped_column(Text, nullable=False, comment="JSON WorldState")


class ChronicleEntryTable(Base):
    """
    Таблица страниц летописи о сражениях.
    Переживает партию: летописи прошлых игр читаются из главного меню.
    """

    __tablename__ = "chronicle_entries"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, comment="UUID записи летописи"
    )
    battle_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="Бой, о котором написана страница"
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="Название сражения")
    quote: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="Цитата эпохи")
    body: Mapped[str] = mapped_column(Text, nullable=False, comment="Текст летописи")

    tick: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Глобальный такт события"
    )
    location_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", comment="Место сражения"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        comment="Дата и время записи",
    )


class FallenRecordTable(Base):
    """
    Таблица надгробий Зала павших.
    Сюда попадают только именные отряды и герои - безымянных хоронят
    общими словами в самой летописи.
    """

    __tablename__ = "fallen_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, comment="UUID надгробия"
    )
    squad_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Имя, под которым его запомнили"
    )
    commander_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", comment="Имя командира"
    )
    race_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="Раса павшего")

    biography: Mapped[str] = mapped_column(Text, nullable=False, comment="Некролог от летописца")

    death_tick: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Такт гибели"
    )
    killer_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", comment="Кто их положил"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        comment="Дата и время записи",
    )
