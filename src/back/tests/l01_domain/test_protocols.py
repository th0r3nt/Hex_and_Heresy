"""
Тесты соответствия протоколам src/back/l01_domain/protocols/
"""

from typing import Any, Callable, Coroutine, Optional
from pydantic import BaseModel
import pytest

from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.army.models.card.unit import UnitArchetype
from src.back.l01_domain.army.models.characters.commanders import (
    CommanderArchetype,
    CommanderTrait,
)
from src.back.l01_domain.factions.models.buildings import Building

from src.back.l01_domain.protocols.chronicler import ChroniclerRepositoryProtocol
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l01_domain.protocols.saves import SaveGameRepositoryProtocol
from src.back.l01_domain.world.models.state import WorldState

# ==================================================================
# FAKE IMPLEMENTATIONS ДЛЯ ТЕСТИРОВАНИЯ КОНТРАКТОВ
# ==================================================================


class FakeLLMClient:
    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        return "fake generated text"

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        temperature: float = 0.2,
    ) -> BaseModel:
        return response_model()


class FakeGameDataRepository:
    def get_unit_archetype(self, unit_id: str) -> Optional[UnitArchetype]:
        return None

    def get_equipment(self, equipment_id: str) -> Optional[Equipment]:
        return None

    def get_building(self, building_id: str) -> Optional[Building]:
        return None

    def get_commander_archetype(self, archetype_id: str) -> Optional[CommanderArchetype]:
        return None

    def get_commander_trait(self, trait_id: str) -> Optional[CommanderTrait]:
        return None

    def list_faction_units(self, faction_id: str) -> list[UnitArchetype]:
        return []

    def list_faction_equipment(self, faction_id: str) -> list[Equipment]:
        return []

    def list_faction_buildings(self, faction_id: str) -> list[Building]:
        return []


class FakeSaveGameRepository:
    async def save_world_state(self, save_id: str, save_name: str, state: WorldState) -> None:
        pass

    async def load_world_state(self, save_id: str) -> Optional[WorldState]:
        return None

    async def list_saves(self) -> list[dict[str, Any]]:
        return []

    async def delete_save(self, save_id: str) -> bool:
        return True


class FakeChroniclerRepository:
    async def record_battle_history(
        self,
        battle_id: str,
        title: str,
        quote: str,
        body: str,
        tick: int,
        location_name: str,
    ) -> None:
        pass

    async def record_fallen_squad(
        self,
        squad_name: str,
        commander_name: str,
        race_id: str,
        biography: str,
        death_tick: int,
        killer_name: str,
    ) -> None:
        pass

    async def get_history_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        return []

    async def get_fallen_records(self, limit: int = 50) -> list[dict[str, Any]]:
        return []


class FakeEventBus:
    def subscribe(
        self, event_name: str, handler: Callable[..., Coroutine[Any, Any, None] | Any]
    ) -> None:
        pass

    def unsubscribe(
        self, event_name: str, handler: Callable[..., Coroutine[Any, Any, None] | Any]
    ) -> None:
        pass

    async def publish(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        pass


class IncompleteClient:
    """Неполный класс для проверки отклонения несовместимых реализаций."""

    def generate_text(self) -> str:
        return ""


# ==================================================================
# ТЕСТЫ
# ==================================================================


class TestProtocolsCompliance:
    def test_llm_client_protocol(self):
        client = FakeLLMClient()
        assert isinstance(client, LLMClientProtocol)
        assert not isinstance(IncompleteClient(), LLMClientProtocol)

    def test_gamedata_repository_protocol(self):
        repo = FakeGameDataRepository()
        assert isinstance(repo, GameDataRepositoryProtocol)
        assert not isinstance(IncompleteClient(), GameDataRepositoryProtocol)

    def test_save_game_repository_protocol(self):
        repo = FakeSaveGameRepository()
        assert isinstance(repo, SaveGameRepositoryProtocol)
        assert not isinstance(IncompleteClient(), SaveGameRepositoryProtocol)

    def test_chronicler_repository_protocol(self):
        repo = FakeChroniclerRepository()
        assert isinstance(repo, ChroniclerRepositoryProtocol)
        assert not isinstance(IncompleteClient(), ChroniclerRepositoryProtocol)

    def test_event_bus_protocol(self):
        bus = FakeEventBus()
        assert isinstance(bus, EventBusProtocol)
        assert not isinstance(IncompleteClient(), EventBusProtocol)

    @pytest.mark.asyncio
    async def test_fake_llm_execution(self):
        class DummyOutput(BaseModel):
            value: int = 42

        client = FakeLLMClient()
        text = await client.generate_text(system_prompt="sys", user_prompt="user")
        structured = await client.generate_structured(
            system_prompt="sys", user_prompt="user", response_model=DummyOutput
        )

        assert text == "fake generated text"
        assert structured.value == 42
