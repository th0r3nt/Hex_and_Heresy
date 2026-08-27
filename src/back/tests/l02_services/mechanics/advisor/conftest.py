"""
Общие фикстуры ставки советника: фракция с казной, фейковая шина событий
и скриптованная языковая модель.

Сборщики промптов и контекста приезжают из tests/l02_services/conftest.py:
фикстуры fake_prompt_builder и fake_context_builder.
"""

from typing import Any, Optional

import pytest
from pydantic import BaseModel

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.advisor import (
    AdvisorOptionKind,
    LLMAdvisorOption,
    LLMAdvisorProposalResponse,
)
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.advisor.facade import AdvisorFacade
from src.back.l02_services.mechanics.advisor.generation import AdvisorGenerator


# ==================================================================
# ФЕЙКОВОЕ ОКРУЖЕНИЕ
# ==================================================================


class FakeEventBus:
    """Шина событий, запоминающая опубликованное."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        self.events.append((event_name, kwargs))

    def names(self) -> list[str]:
        return [name for name, _ in self.events]

    def payload_of(self, event_name: str) -> dict:
        for name, payload in self.events:
            if name == event_name:
                return payload
        return {}


class FakeLLMClient:
    """
    Советник со скриптованными ответами.

    Запоминает промпты: тестам важно не только что сказала модель,
    но и что ей отдали на вход.
    """

    def __init__(self) -> None:
        self.structured_response: Optional[BaseModel] = None
        self.text_response: str = "Как прикажете, мой лорд."
        self.error: Optional[Exception] = None

        self.structured_calls: list[dict[str, Any]] = []
        self.text_calls: list[dict[str, Any]] = []

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> str:
        self.text_calls.append(
            {"system_prompt": system_prompt, "user_prompt": user_prompt}
        )
        if self.error is not None:
            raise self.error
        return self.text_response

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        temperature: float = 0.6,
    ) -> BaseModel:
        self.structured_calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": response_model,
            }
        )
        if self.error is not None:
            raise self.error
        if self.structured_response is None:
            raise AssertionError("FakeLLMClient: ответ советника не задан")
        return self.structured_response


# ==================================================================
# ОТВЕТЫ СОВЕТНИКА
# ==================================================================


def build_proposal_response(**overrides) -> LLMAdvisorProposalResponse:
    """Канонический совет из advisor.md: поднять налоги."""
    data = {
        "should_speak": True,
        "title": "Казна пуста",
        "message": (
            "Мой лорд, налоги в графстве занижены. Предлагаю поднять сбор на 10%."
        ),
        "options": [
            LLMAdvisorOption(label="Принять", kind=AdvisorOptionKind.ACCEPT),
            LLMAdvisorOption(label="Поднять на 5%", kind=AdvisorOptionKind.ADJUST),
            LLMAdvisorOption(label="Отклонить", kind=AdvisorOptionKind.DECLINE),
        ],
    }
    data.update(overrides)
    return LLMAdvisorProposalResponse(**data)


def build_silent_response() -> LLMAdvisorProposalResponse:
    """В державе спокойно - советник молчит."""
    return LLMAdvisorProposalResponse(should_speak=False)


@pytest.fixture
def proposal_response():
    """Фабрика советов (тестовые модули лежат вне пакета)."""
    return build_proposal_response


@pytest.fixture
def silent_response():
    """Фабрика молчания советника."""
    return build_silent_response


# ==================================================================
# ИГРОВОЙ МИР
# ==================================================================


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def humans() -> Faction:
    """Фракция игрока с полной казной."""
    faction = Faction(
        id="humans",
        race=FactionRace.HUMANS,
        name="Священная Империя",
        lord=Lord(faction_id="humans", name="Лорд Отто", title="Барон"),
        headquarters=Headquarters(faction_id="humans", name="Цитадель"),
        capital_hex=HexCoordinates.from_axial(0, 0),
        is_player_controlled=True,
    )
    faction.resources[ResourceType.GOLD] = 1000.0
    faction.resources[ResourceType.MATERIAL] = 1000.0
    faction.resources[ResourceType.FOOD] = 500.0
    return faction


@pytest.fixture
def world(humans: Faction) -> WorldState:
    state = WorldState()
    state.add_faction(humans)
    return state


@pytest.fixture
def llm() -> FakeLLMClient:
    """Советник без готового ответа: тест сам укладывает нужный."""
    return FakeLLMClient()


@pytest.fixture
def generator(llm, fake_prompt_builder, fake_context_builder) -> AdvisorGenerator:
    return AdvisorGenerator(
        llm_client=llm,
        prompt_builder=fake_prompt_builder,
        context_builder=fake_context_builder,
    )


@pytest.fixture
def facade(llm, fake_bus, fake_prompt_builder, fake_context_builder) -> AdvisorFacade:
    """
    Ставка советника на доменных фейках: ни файлов промптов с диска,
    ни настоящего сборщика контекста.

    Пауза между советами убрана: тесты проверяют ее отдельно.
    """
    return AdvisorFacade(
        llm_client=llm,
        prompt_builder=fake_prompt_builder,
        context_builder=fake_context_builder,
        event_bus=fake_bus,
        proposal_interval=0,
    )
