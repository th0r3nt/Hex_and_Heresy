"""
Общие фикстуры мастерской: фракция с казной, фейковая шина событий
и детерминированная языковая модель.

Сборщики промптов и контекста приезжают из tests/l02_services/conftest.py:
фикстуры fake_prompt_builder и fake_context_builder.
"""

from typing import Any, Optional

import pytest
from pydantic import BaseModel

from src.back.l01_domain.army.constants import EquipmentSlot, EquipmentTag
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.gunsmith.crafting import (
    LLMGunsmithResponse,
    StatPriorities,
)
from src.back.l02_services.mechanics.gunsmith.facade import GunsmithFacade


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
    Мастер-оружейник со скриптованным ответом.

    Запоминает промпты: тестам важно не только что вернула модель,
    но и что ей отдали на вход.
    """

    def __init__(self, response: Optional[LLMGunsmithResponse] = None) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> str:
        return "Мастер что-то бурчит себе под нос."

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        temperature: float = 0.6,
    ) -> BaseModel:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": response_model,
            }
        )
        if self.response is None:
            raise AssertionError("FakeLLMClient: ответ мастера не задан")
        return self.response


# ==================================================================
# ОТВЕТЫ МАСТЕРА
# ==================================================================


def build_approved_response(**overrides) -> LLMGunsmithResponse:
    """Одобренный заказ: тяжелая двуручная алебарда с пороховым стволом."""
    data = {
        "is_approved": True,
        "master_reply": "Тяжелая выйдет, но я такое уже ковал. Держите чертеж.",
        "name": "Алебарда с аркебузой",
        "lore": "Древко, к которому прикручен однозарядный ствол.",
        "tier": 3,
        "slot": EquipmentSlot.WEAPON,
        "category_name": "polearm",
        "tags": [EquipmentTag.TWO_HANDED, EquipmentTag.HEAVY, EquipmentTag.BLACKPOWDER],
        "priorities": StatPriorities(
            damage=8, armor_piercing=4, heavy_weight_tradeoff=5, clunkiness_tradeoff=2
        ),
    }
    data.update(overrides)
    return LLMGunsmithResponse(**data)


def build_rejected_response(
    reply: str = "Магический посох? В Империи за такое жгут. Вон отсюда.",
) -> LLMGunsmithResponse:
    """Отказ мастера: заказ противоречит лору фракции."""
    return LLMGunsmithResponse(is_approved=False, master_reply=reply)


@pytest.fixture
def approved_response():
    """Фабрика одобренных ответов (тестовые модули лежат вне пакета)."""
    return build_approved_response


@pytest.fixture
def rejected_response():
    """Фабрика отказов мастера."""
    return build_rejected_response


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
    """Мастер без готового ответа: тест сам укладывает нужный в llm.response."""
    return FakeLLMClient()


@pytest.fixture
def facade(llm, fake_bus, fake_prompt_builder, fake_context_builder) -> GunsmithFacade:
    """
    Мастерская на доменных фейках: ни файлов промптов с диска,
    ни настоящего сборщика контекста.
    """
    return GunsmithFacade(
        llm_client=llm,
        prompt_builder=fake_prompt_builder,
        context_builder=fake_context_builder,
        event_bus=fake_bus,
    )
