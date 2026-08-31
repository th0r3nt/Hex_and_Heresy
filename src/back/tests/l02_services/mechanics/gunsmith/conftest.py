"""
Общие фикстуры мастерской: фракция с казной, фейковая шина событий
и детерминированная языковая модель.

Мастер отвечает правителю только вызовами навыков (Function Calling), поэтому
фейковая модель отдает пары «свободный текст + список вызовов».

Сборщики промптов и контекста приезжают из tests/l02_services/conftest.py:
фикстуры fake_prompt_builder и fake_context_builder.
"""

from typing import Any, Optional

import pytest

from src.back.l01_domain.army.constants import EquipmentSlot, EquipmentTag
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.llm.models.tools import ToolCall, ToolDefinition
from src.back.l01_domain.llm.tools.definitions.gunsmith import (
    DRAFT_BLUEPRINT,
    REJECT_BLUEPRINT,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.gunsmith.facade import GunsmithFacade
from src.back.tests.l02_services.fakes import LLMReply, tool_call

MASTER_APPROVAL = "Тяжелая выйдет, но я такое уже ковал. Держите чертеж."
MASTER_REFUSAL = "Магический посох? В Империи за такое жгут. Вон отсюда."


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

    Ответы укладываются очередью (`script`) в порядке заказов. Запоминает
    промпты: тестам важно не только что вернула модель, но и что ей отдали
    на вход.
    """

    def __init__(self) -> None:
        self.replies: list[LLMReply] = []
        self.calls: list[dict[str, Any]] = []

    def script(self, *replies: LLMReply) -> None:
        self.replies.extend(replies)

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> str:
        return "Мастер что-то бурчит себе под нос."

    async def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
        temperature: float = 0.6,
        tool_choice: Any = "auto",
    ) -> tuple[str, list[ToolCall]]:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "tools": list(tools),
            }
        )
        if not self.replies:
            raise AssertionError("FakeLLMClient: ответ мастера не задан")
        content, calls = self.replies.pop(0)
        return content, list(calls)


# ==================================================================
# ОТВЕТЫ МАСТЕРА
# ==================================================================


def build_draft_call(**overrides) -> ToolCall:
    """Одобренный заказ: тяжелая двуручная алебарда с пороховым стволом."""
    arguments: dict[str, Any] = {
        "name": "Алебарда с аркебузой",
        "lore": "Древко, к которому прикручен однозарядный ствол.",
        "slot": EquipmentSlot.WEAPON.value,
        "category_name": "polearm",
        "tier": 3,
        "tags": [
            EquipmentTag.TWO_HANDED.value,
            EquipmentTag.HEAVY.value,
            EquipmentTag.BLACKPOWDER.value,
        ],
        "damage_priority": 8,
        "armor_piercing_priority": 4,
        "heavy_weight_tradeoff": 5,
        "clunkiness_tradeoff": 2,
        "master_reply": MASTER_APPROVAL,
    }
    arguments.update(overrides)
    return tool_call(DRAFT_BLUEPRINT.name, **arguments)


def build_reject_call(master_reply: str = MASTER_REFUSAL, **overrides) -> ToolCall:
    """Отказ мастера: заказ противоречит лору фракции."""
    arguments: dict[str, Any] = {
        "reason": "Заказ противоречит лору фракции.",
        "master_reply": master_reply,
    }
    arguments.update(overrides)
    return tool_call(REJECT_BLUEPRINT.name, **arguments)


@pytest.fixture
def draft_call():
    """Фабрика вызовов навыка чертежа (тестовые модули лежат вне пакета)."""
    return build_draft_call


@pytest.fixture
def reject_call():
    """Фабрика вызовов навыка отказа."""
    return build_reject_call


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
    """Мастер без готового ответа: тест сам укладывает нужный через llm.script."""
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
