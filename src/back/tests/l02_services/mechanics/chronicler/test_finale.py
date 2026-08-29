"""
Последняя глава хроники: ода триумфатору или реквием павшей державе.

Финал - украшение экрана окончания, а не игровое правило, поэтому здесь же
проверяется, что молчащая модель ничего не ломает: подпись под финалом
должна остаться в любом случае.
"""

import pytest

from src.back.l01_domain.exceptions.llm import LLMRequestFailedError
from src.back.l01_domain.world.constants import VictoryType
from src.back.l01_domain.world.models.chronicle import LLMFinaleResponse
from src.back.l01_domain.world.models.victory import (
    VictoryEvaluationResult,
    VictoryProgress,
)
from src.back.l02_services.mechanics.chronicler.facade import ChroniclerFacade
from src.back.utils.event.registry import GameEvents

FINALE_RECORDED = GameEvents.Chronicler.FINALE_RECORDED


@pytest.fixture
def facade(
    fake_llm, fake_repository, fake_bus, fake_prompt_builder, fake_context_builder
) -> ChroniclerFacade:
    return ChroniclerFacade(
        llm_client=fake_llm,
        repository=fake_repository,
        event_bus=fake_bus,
        prompt_builder=fake_prompt_builder,
        context_builder=fake_context_builder,
    )


@pytest.fixture
def mute_facade(fake_repository, fake_bus) -> ChroniclerFacade:
    """Летописец без языковой модели: он только ведет учет."""
    return ChroniclerFacade(repository=fake_repository, event_bus=fake_bus)


def victory_result(
    winner_id: str = "humans", victory_type: VictoryType = VictoryType.EXPANSION
) -> VictoryEvaluationResult:
    return VictoryEvaluationResult(
        is_game_over=True,
        is_player_victorious=True,
        victory_type=victory_type,
        winner_faction_id=winner_id,
        reason="Основание страны. Три крепости связали Ничью землю.",
        progress={
            winner_id: VictoryProgress(
                faction_id=winner_id,
                current_gold=1200.0,
                max_level_towns_count=3,
            )
        },
    )


class TestFinaleWriting:
    @pytest.mark.asyncio
    async def test_finale_is_written_into_the_world(self, facade, world, fake_bus):
        finale = await facade.write_finale(world, victory_result())

        assert finale is not None
        assert world.finale is finale
        assert finale.title == "Последняя глава"
        assert finale.victory_type is VictoryType.EXPANSION
        assert FINALE_RECORDED in fake_bus.names()

    @pytest.mark.asyncio
    async def test_outcome_numbers_reach_the_model(self, facade, world, fake_llm):
        await facade.write_finale(world, victory_result())

        call = fake_llm.structured_calls[-1]
        assert call["response_model"] is LLMFinaleResponse
        assert "Городов 4-го уровня: 3." in call["user_prompt"]

    @pytest.mark.asyncio
    async def test_unfinished_party_gets_no_finale(self, facade, world, fake_bus):
        finale = await facade.write_finale(world, VictoryEvaluationResult())

        assert finale is None
        assert world.finale is None
        assert FINALE_RECORDED not in fake_bus.names()

    @pytest.mark.asyncio
    async def test_finale_is_written_only_once(self, facade, world, fake_bus):
        first = await facade.write_finale(world, victory_result())

        assert await facade.write_finale(world, victory_result()) is None
        assert world.finale is first
        assert fake_bus.names().count(FINALE_RECORDED) == 1


class TestFinaleWithoutTheModel:
    @pytest.mark.asyncio
    async def test_mute_chronicler_still_records_the_reason(self, mute_facade, world):
        """Без модели экран финала все равно получает подпись под исходом."""
        result = victory_result()

        finale = await mute_facade.write_finale(world, result)

        assert finale is not None
        assert finale.body == ""
        assert finale.reason == result.reason

    @pytest.mark.asyncio
    async def test_failed_generation_does_not_lose_the_finale(
        self, facade, world, fake_llm
    ):
        async def refuse(*_args, **_kwargs):
            raise LLMRequestFailedError("local", "model", "нет сети")

        fake_llm.generate_structured = refuse

        finale = await facade.write_finale(world, victory_result())

        assert finale is not None
        assert finale.body == ""
        assert world.finale is finale
