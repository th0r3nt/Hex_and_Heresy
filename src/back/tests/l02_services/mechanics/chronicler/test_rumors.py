"""
Тесты фоновых слухов: молчание во время боев, сборка сводки мира и запись
слуха в окно логов.
"""

import pytest

from src.back.l01_domain.exceptions import LLMRequestFailedError
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.world.constants import (
    RUMOR_IDLE_TICKS_THRESHOLD,
    RUMOR_TEXT_MAX_LENGTH,
)
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.constants import GlobalEventCategory
from src.back.l02_services.mechanics.chronicler.facade import ChroniclerFacade
from src.back.l02_services.mechanics.chronicler.generation.rumors import RumorGenerator
from src.back.utils.event.registry import GameEvents


@pytest.fixture
def generator(fake_llm) -> RumorGenerator:
    return RumorGenerator(fake_llm)


class TestShouldSpeak:
    def test_silent_while_battles_rage(self, generator, world):
        world.ticks_since_last_battle = 0

        assert generator.should_speak(world) is False

    def test_speaks_after_enough_silence(self, generator, world):
        world.ticks_since_last_battle = RUMOR_IDLE_TICKS_THRESHOLD

        assert generator.should_speak(world) is True

    def test_threshold_can_be_overridden(self, generator, world):
        world.ticks_since_last_battle = 1

        assert generator.should_speak(world, idle_threshold=1) is True


class TestWorldContext:
    def test_context_lists_time_and_silence(self, generator, world):
        world.ticks_since_last_battle = 4

        context = generator.render_world_context(world)

        assert "Текущее время: Год 1" in context
        assert "Тактов без боев: 4" in context

    def test_context_mentions_active_events(self, generator, world):
        world.add_event(
            GlobalEvent(
                name="Магнитная буря",
                description="Небо трещит.",
                category=GlobalEventCategory.WEATHER,
            )
        )

        assert "«Магнитная буря»" in generator.render_world_context(world)

    def test_context_mentions_wars_by_name(self, generator, world):
        world.get_or_create_relation("humans", "greenskins").declare_war()

        context = generator.render_world_context(world)

        assert "Священная Империя против Орда Ржавых Клыков" in context

    def test_context_notices_hunger(self, generator, world, humans):
        humans.resources[ResourceType.FOOD] = 10.0

        context = generator.render_world_context(world, humans)

        assert "нехватки провизии" in context

    def test_well_fed_faction_does_not_complain(self, generator, world, humans):
        humans.resources[ResourceType.FOOD] = 500.0

        assert "нехватки провизии" not in generator.render_world_context(world, humans)


class TestRumorGeneration:
    @pytest.mark.asyncio
    async def test_rumor_carries_tick_and_faction(self, generator, world, humans):
        world.time.advance_ticks(6)

        rumor = await generator.generate_rumor(world, humans)

        assert rumor is not None
        assert rumor.text == "Торговцы говорят, что барон опять поднял налоги."
        assert rumor.tick == 6
        assert rumor.faction_id == "humans"

    @pytest.mark.asyncio
    async def test_empty_answer_produces_nothing(self, world, humans, fake_llm):
        fake_llm.rumor = "   "

        assert await RumorGenerator(fake_llm).generate_rumor(world, humans) is None

    @pytest.mark.asyncio
    async def test_talkative_model_is_trimmed(self, world, humans, fake_llm):
        fake_llm.rumor = "С" * (RUMOR_TEXT_MAX_LENGTH + 100)

        rumor = await RumorGenerator(fake_llm).generate_rumor(world, humans)

        assert rumor is not None
        assert len(rumor.text) == RUMOR_TEXT_MAX_LENGTH

    @pytest.mark.asyncio
    async def test_model_failure_is_swallowed(self, world, humans):
        class BrokenLLM:
            async def generate_text(self, *args, **kwargs):
                raise LLMRequestFailedError("local", "model", "нет сети")

            async def generate_structured(self, *args, **kwargs):
                raise LLMRequestFailedError("local", "model", "нет сети")

        assert await RumorGenerator(BrokenLLM()).generate_rumor(world, humans) is None


class TestFacadeRumors:
    @pytest.mark.asyncio
    async def test_facade_stays_quiet_until_the_threshold(self, world, fake_llm, fake_bus):
        facade = ChroniclerFacade(llm_client=fake_llm, event_bus=fake_bus)
        world.ticks_since_last_battle = RUMOR_IDLE_TICKS_THRESHOLD - 1

        assert await facade.speak_rumor(world) is None
        assert fake_llm.text_calls == []

    @pytest.mark.asyncio
    async def test_facade_records_rumor_and_publishes_event(self, world, fake_llm, fake_bus):
        facade = ChroniclerFacade(llm_client=fake_llm, event_bus=fake_bus)
        world.ticks_since_last_battle = RUMOR_IDLE_TICKS_THRESHOLD

        rumor = await facade.speak_rumor(world)

        assert rumor is not None
        assert world.rumors == [rumor]
        assert facade.get_rumors(world) == [rumor]
        assert GameEvents.Chronicler.RUMOR_GENERATED in fake_bus.names()

    @pytest.mark.asyncio
    async def test_rumor_is_written_for_the_player_by_default(self, world, fake_llm, fake_bus):
        facade = ChroniclerFacade(llm_client=fake_llm, event_bus=fake_bus)
        world.ticks_since_last_battle = RUMOR_IDLE_TICKS_THRESHOLD

        rumor = await facade.speak_rumor(world)

        assert rumor is not None
        assert rumor.faction_id == "humans"

    async def test_race_style_reaches_the_prompt(
        self, generator, world, greenskins, fake_llm, fake_prompt_builder
    ):
        # Подменяем билдер в генераторе слухов
        generator._prompt_builder = fake_prompt_builder
        await generator.generate_rumor(world, greenskins)

        # Проверяем, что слух запросил лорный файл зеленокожих
        assert "[factions/greenskins.md]" in fake_llm.text_calls[0]["system_prompt"]
        assert "[roles/chronicler/prompt.md]" in fake_llm.text_calls[0]["system_prompt"]
