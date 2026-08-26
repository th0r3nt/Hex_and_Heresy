"""
Тесты генератора кастомных полководцев через мастера игры.
"""

from typing import Any, Optional
import pytest
from pydantic import BaseModel

from src.back.l01_domain.common import CharacterGenerationType, FactionRace, StatName
from src.back.l01_domain.exceptions.llm import LLMRequestFailedError
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l02_services.mechanics.game_master.custom.commanders import (
    CustomCommanderDraftResponse,
    CustomCommanderFactory,
)
from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder


class FakeLLMClient(LLMClientProtocol):
    """Фейковый клиент языковых моделей для тестов."""

    def __init__(self, draft_response: Optional[BaseModel] = None) -> None:
        self.draft_response = draft_response
        self.calls: list[dict[str, Any]] = []

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> str:
        return "Текст"

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
        if self.draft_response is None:
            return response_model.model_validate({})
        return self.draft_response


class FakePromptBuilder(PromptBuilder):
    def __init__(self) -> None:
        pass

    def build(self, keys: list[str]) -> str:
        return "\n\n".join(f"[{key}]" for key in keys)


@pytest.fixture
def fake_prompt_builder() -> FakePromptBuilder:
    return FakePromptBuilder()


class TestCustomCommanderFactory:
    @pytest.mark.asyncio
    async def test_successful_commander_generation_with_traits(self, fake_prompt_builder):
        draft = CustomCommanderDraftResponse(
            is_lore_friendly=True,
            name="Сержант Ганс",
            archetype_name="Окопный ветеран",
            archetype_description="Мастер позиционной обороны.",
            distilled_personality="Циничный и подозрительный солдат.",
            selected_trait_ids=["craven", "deserter"],
            authority=45,
            tactical_acumen=60,
            resilience=70,
            cunning=50,
        )
        llm = FakeLLMClient(draft_response=draft)
        factory = CustomCommanderFactory(llm_client=llm, prompt_builder=fake_prompt_builder)

        commander, message = await factory.create_commander(
            faction_id="humans",
            race=FactionRace.HUMANS,
            biography_text="Старый сержант, выживший в бойне с гоблинами.",
        )

        assert commander is not None
        assert commander.name == "Сержант Ганс"
        assert commander.generation_type == CharacterGenerationType.CUSTOM
        assert commander.characteristics.tactical_acumen == 60
        assert commander.characteristics.resilience == 70
        assert len(commander.traits) == 2

        # Проверяем подтянутые черты из каталога
        trait_ids = [t.id for t in commander.traits]
        assert "trait_craven" in trait_ids
        assert "trait_deserter" in trait_ids

        # Проверяем агрегацию модификаторов
        modifiers = commander.get_active_modifiers()
        stat_names = {m.stat_name for m in modifiers}
        assert StatName.MORALE in stat_names
        assert StatName.AMBUSH_RESISTANCE in stat_names

        assert "готов занять место" in message

    @pytest.mark.asyncio
    async def test_lore_rejection_returns_none_with_reason(self, fake_prompt_builder):
        draft = CustomCommanderDraftResponse(
            is_lore_friendly=False,
            rejection_reason="Запрос отклонен Залом инквизиции: кибернетика и лазеры запрещены.",
        )
        llm = FakeLLMClient(draft_response=draft)
        factory = CustomCommanderFactory(llm_client=llm, prompt_builder=fake_prompt_builder)

        commander, message = await factory.create_commander(
            faction_id="humans",
            race=FactionRace.HUMANS,
            biography_text="Киборг-терминатор с лазерным мечом.",
        )

        assert commander is None
        assert "Залом инквизиции" in message

    @pytest.mark.asyncio
    async def test_llm_failure_handling(self, fake_prompt_builder):
        class BrokenLLM(LLMClientProtocol):
            async def generate_text(self, *args, **kwargs) -> str:
                raise LLMRequestFailedError("local", "model", "сеть недоступна")

            async def generate_structured(self, *args, **kwargs):
                raise LLMRequestFailedError("local", "model", "сеть недоступна")

        factory = CustomCommanderFactory(
            llm_client=BrokenLLM(), prompt_builder=fake_prompt_builder
        )

        commander, message = await factory.create_commander(
            faction_id="humans",
            race=FactionRace.HUMANS,
            biography_text="Обычный офицер.",
        )

        assert commander is None
        assert "временно недоступен" in message
