"""
Протокол репозитория летописца и Зала павших.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ChroniclerRepositoryProtocol(Protocol):
    """
    Контракт сохранения нарративных записей летописца и некрологов Зала павших.
    """

    async def record_battle_history(
        self,
        battle_id: str,
        title: str,
        quote: str,
        body: str,
        tick: int,
        location_name: str,
    ) -> None:
        ...

    async def record_fallen_squad(
        self,
        squad_name: str,
        commander_name: str,
        race_id: str,
        biography: str,
        death_tick: int,
        killer_name: str,
    ) -> None:
        ...

    async def get_history_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        ...

    async def get_fallen_records(self, limit: int = 50) -> list[dict[str, Any]]:
        ...