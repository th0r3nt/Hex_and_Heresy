"""
Протокол репозитория сохранений игры.
"""

from typing import Any, Optional, Protocol, runtime_checkable

from src.back.l01_domain.world.models.state import WorldState


@runtime_checkable
class SaveGameRepositoryProtocol(Protocol):
    """
    Контракт сохранения и загрузки снимка состояния партии (БД SQLite).
    """

    async def save_world_state(
        self, save_id: str, save_name: str, state: WorldState
    ) -> None:
        ...

    async def load_world_state(self, save_id: str) -> Optional[WorldState]:
        ...

    async def list_saves(self) -> list[dict[str, Any]]:
        ...

    async def delete_save(self, save_id: str) -> bool:
        ...