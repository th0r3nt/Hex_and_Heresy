"""
Тесты хранилища летописи и Зала павших на настоящей (in-memory) SQLite.

Проверяют контракт ChroniclerRepositoryProtocol целиком: запись, чтение
и защиту от дублей, из-за которой один бой не попадет в книгу дважды.
"""

import pytest
from typing import AsyncGenerator

from src.back.l01_domain.protocols.chronicler import ChroniclerRepositoryProtocol
from src.back.l03_infrastructure.databases.manager import DatabaseManager
from src.back.l03_infrastructure.databases.sql.db import SQLDB


@pytest.fixture
async def manager() -> AsyncGenerator[DatabaseManager, None]:
    """
    Чистая база на каждый тест с корректным освобождением ресурсов.
    """
    db = SQLDB(db_url="sqlite+aiosqlite:///:memory:")
    await db.init_tables()

    yield DatabaseManager(db.session_factory)

    # Очистка пула после выполнения теста
    await db.dispose()


class TestProtocolCompliance:
    def test_manager_implements_the_contract(self):
        assert issubclass(DatabaseManager, ChroniclerRepositoryProtocol)


class TestChronicleHistory:
    @pytest.mark.asyncio
    async def test_entry_is_written_and_read_back(self, manager):
        await manager.record_battle_history(
            battle_id="battle_1",
            title="Резня в Долине ржавых мечей",
            quote="Они умерли за Империю.",
            body="Строй сошелся со строем.",
            tick=12,
            location_name="Ничья земля (4, 0)",
        )

        entries = await manager.get_history_entries()

        assert len(entries) == 1
        assert entries[0]["battle_id"] == "battle_1"
        assert entries[0]["title"] == "Резня в Долине ржавых мечей"
        assert entries[0]["tick"] == 12

    @pytest.mark.asyncio
    async def test_one_battle_is_written_once(self, manager):
        for title in ("Первая версия", "Вторая версия"):
            await manager.record_battle_history(
                battle_id="battle_1",
                title=title,
                quote="",
                body="Текст.",
                tick=1,
                location_name="Ничья земля",
            )

        entries = await manager.get_history_entries()

        assert len(entries) == 1
        assert entries[0]["title"] == "Первая версия"

    @pytest.mark.asyncio
    async def test_limit_is_respected(self, manager):
        for i in range(5):
            await manager.record_battle_history(
                battle_id=f"battle_{i}",
                title=f"Бой {i}",
                quote="",
                body="Текст.",
                tick=i,
                location_name="Ничья земля",
            )

        assert len(await manager.get_history_entries(limit=3)) == 3

    @pytest.mark.asyncio
    async def test_empty_archive_is_not_an_error(self, manager):
        assert await manager.get_history_entries() == []


class TestHallOfFallen:
    @pytest.mark.asyncio
    async def test_record_is_written_and_read_back(self, manager):
        await manager.record_fallen_squad(
            squad_name="Грязные стрелки Маркуса",
            commander_name="Маркус",
            race_id="humans",
            biography="Держали фланг до последнего болта.",
            death_tick=30,
            killer_name="greenskins",
        )

        records = await manager.get_fallen_records()

        assert len(records) == 1
        assert records[0]["squad_name"] == "Грязные стрелки Маркуса"
        assert records[0]["commander_name"] == "Маркус"
        assert records[0]["death_tick"] == 30

    @pytest.mark.asyncio
    async def test_squad_is_buried_once_per_tick(self, manager):
        for biography in ("Первый некролог", "Второй некролог"):
            await manager.record_fallen_squad(
                squad_name="Грязные стрелки Маркуса",
                commander_name="Маркус",
                race_id="humans",
                biography=biography,
                death_tick=30,
                killer_name="greenskins",
            )

        records = await manager.get_fallen_records()

        assert len(records) == 1
        assert records[0]["biography"] == "Первый некролог"

    @pytest.mark.asyncio
    async def test_same_name_in_another_battle_is_a_separate_grave(self, manager):
        """Имя отряда переиспользуется между партиями - такт гибели их разводит."""
        for tick in (30, 90):
            await manager.record_fallen_squad(
                squad_name="Грязные стрелки Маркуса",
                commander_name="Маркус",
                race_id="humans",
                biography="Полегли у ворот.",
                death_tick=tick,
                killer_name="greenskins",
            )

        assert len(await manager.get_fallen_records()) == 2
