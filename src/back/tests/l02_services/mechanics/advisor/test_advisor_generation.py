"""
Тесты разговора с советником: сборка его промпта, разбор ответа модели
и заглушка выбора навыков.

Генератор - это переводчик между моделью и доменом: он не решает, когда
советнику говорить, но отвечает за то, чтобы окно предложения всегда
соответствовало контракту интерфейса.
"""

import pytest

from src.back.l01_domain.exceptions.advisor import AdvisorGenerationFailedError
from src.back.l01_domain.exceptions.llm import LLMRequestFailedError
from src.back.l01_domain.factions.models.advisor import (
    ADVISOR_MAX_OPTIONS,
    AdvisorOptionKind,
    LLMAdvisorOption,
)
from src.back.l02_services.mechanics.advisor.generation import FREEFORM_OPTION_LABEL

QUESTION = "Какая армия врага ближе всего к столице?"


# ==================================================================
# СИСТЕМНЫЙ ПРОМПТ СОВЕТНИКА
# ==================================================================


class TestSystemPrompt:
    @pytest.mark.asyncio
    async def test_prompt_carries_role_mechanics_and_race(
        self, generator, world, humans, llm, proposal_response
    ):
        """
        У каждой расы свой советник: в промпт уходят его роль, правила
        экономики и стратегии и лор фракции (см. docs/game_mechanics/advisor.md).
        """
        llm.structured_response = proposal_response()

        await generator.generate_proposal(world, humans)

        system_prompt = llm.structured_calls[0]["system_prompt"]
        assert "[base.persona]" in system_prompt
        assert "[base.mechanics.economy]" in system_prompt
        assert "[base.mechanics.strategic]" in system_prompt
        assert "[roles.advisor.prompt]" in system_prompt
        assert "[factions.humans]" in system_prompt
        assert "[lore.basic.medium]" in system_prompt

    @pytest.mark.asyncio
    async def test_prompt_carries_the_current_slice_of_the_world(
        self, generator, world, humans, llm, proposal_response
    ):
        """Советник советует по отчетам, а не вслепую."""
        llm.structured_response = proposal_response()

        await generator.generate_proposal(world, humans)

        assert "[advisor]" in llm.structured_calls[0]["system_prompt"]

    @pytest.mark.asyncio
    async def test_custom_personality_reaches_the_prompt(
        self, generator, world, humans, llm, proposal_response
    ):
        """Личность советника пишет игрок или мастер игры - она обязана доехать."""
        llm.structured_response = proposal_response()

        await generator.generate_proposal(
            world, humans, personality_prompt="Фанатичный инквизитор, говорит приказами."
        )

        assert "Фанатичный инквизитор" in llm.structured_calls[0]["system_prompt"]


# ==================================================================
# ПАССИВНАЯ ИНИЦИАТИВА
# ==================================================================


class TestGenerateProposal:
    @pytest.mark.asyncio
    async def test_proposal_carries_the_advisors_words(
        self, generator, world, humans, llm, proposal_response
    ):
        response = proposal_response()
        llm.structured_response = response

        proposal = await generator.generate_proposal(world, humans)

        assert proposal is not None
        assert proposal.title == response.title
        assert proposal.message == response.message
        assert proposal.faction_id == "humans"

    @pytest.mark.asyncio
    async def test_proposal_remembers_the_tick_it_was_given_on(
        self, generator, world, humans, llm, proposal_response
    ):
        llm.structured_response = proposal_response()
        world.time.total_ticks = 17

        proposal = await generator.generate_proposal(world, humans)

        assert proposal.tick == 17

    @pytest.mark.asyncio
    async def test_silent_advisor_does_not_open_a_window(
        self, generator, world, humans, llm, silent_response
    ):
        """В спокойный такт советник вправе промолчать."""
        llm.structured_response = silent_response()

        assert await generator.generate_proposal(world, humans) is None

    @pytest.mark.asyncio
    async def test_empty_message_is_treated_as_silence(
        self, generator, world, humans, llm, proposal_response
    ):
        """Окно без текста показывать нечем."""
        llm.structured_response = proposal_response(message="   ")

        assert await generator.generate_proposal(world, humans) is None

    @pytest.mark.asyncio
    async def test_broken_model_does_not_break_the_turn(
        self, generator, world, humans, llm
    ):
        """
        Непрошеный совет - украшение хода: отказ модели не должен ронять
        глобальный такт.
        """
        llm.error = LLMRequestFailedError("openai", "gpt", "таймаут")

        assert await generator.generate_proposal(world, humans) is None


# ==================================================================
# КНОПКИ ВЫБОРА
# ==================================================================


class TestOptions:
    @pytest.mark.asyncio
    async def test_options_of_the_model_reach_the_window(
        self, generator, world, humans, llm, proposal_response
    ):
        llm.structured_response = proposal_response()

        proposal = await generator.generate_proposal(world, humans)

        labels = [option.label for option in proposal.options]
        assert labels[:3] == ["Принять", "Поднять на 5%", "Отклонить"]
        assert proposal.options[1].kind == AdvisorOptionKind.ADJUST

    @pytest.mark.asyncio
    async def test_freeform_button_is_always_the_last_one(
        self, generator, world, humans, llm, proposal_response
    ):
        """Возразить советнику своими словами игрок вправе всегда."""
        llm.structured_response = proposal_response()

        proposal = await generator.generate_proposal(world, humans)

        assert proposal.options[-1].label == FREEFORM_OPTION_LABEL
        assert proposal.options[-1].requires_player_text is True

    @pytest.mark.asyncio
    async def test_model_without_options_gets_the_default_pair(
        self, generator, world, humans, llm, proposal_response
    ):
        """Молчаливой модели интерфейс дорисует «Принять» и «Отклонить»."""
        llm.structured_response = proposal_response(options=[])

        proposal = await generator.generate_proposal(world, humans)

        labels = [option.label for option in proposal.options]
        assert labels == ["Принять", "Отклонить", FREEFORM_OPTION_LABEL]

    @pytest.mark.asyncio
    async def test_extra_options_are_cut_to_fit_the_window(
        self, generator, world, humans, llm, proposal_response
    ):
        """Свободный ответ не должен вытесняться болтливостью модели."""
        llm.structured_response = proposal_response(
            options=[LLMAdvisorOption(label=f"Вариант {i}") for i in range(10)]
        )

        proposal = await generator.generate_proposal(world, humans)

        assert len(proposal.options) == ADVISOR_MAX_OPTIONS
        assert proposal.options[-1].requires_player_text is True

    @pytest.mark.asyncio
    async def test_freeform_option_of_the_model_is_not_duplicated(
        self, generator, world, humans, llm, proposal_response
    ):
        """Модель предложила свой ответ сама - кнопка все равно одна."""
        llm.structured_response = proposal_response(
            options=[
                LLMAdvisorOption(label="Принять", kind=AdvisorOptionKind.ACCEPT),
                LLMAdvisorOption(label="Скажу сам", kind=AdvisorOptionKind.FREEFORM),
            ]
        )

        proposal = await generator.generate_proposal(world, humans)

        freeform = [o for o in proposal.options if o.requires_player_text]
        assert len(freeform) == 1


# ==================================================================
# ДИАЛОГОВЫЙ РЕЖИМ
# ==================================================================


class TestAnswerQuestion:
    @pytest.mark.asyncio
    async def test_question_reaches_the_model_and_the_answer_comes_back(
        self, generator, world, humans, llm
    ):
        llm.text_response = "Орда зеленокожих в двух переходах от столицы, мой лорд."

        answer = await generator.answer_question(world, humans, QUESTION)

        assert answer.question == QUESTION
        assert answer.text == llm.text_response
        assert QUESTION in llm.text_calls[0]["user_prompt"]

    @pytest.mark.asyncio
    async def test_broken_model_is_a_refusal_to_serve(
        self, generator, world, humans, llm
    ):
        """
        Игрок открыл окно и ждет ответа: молчание модели здесь уже ошибка.
        """
        llm.error = LLMRequestFailedError("openai", "gpt", "таймаут")

        with pytest.raises(AdvisorGenerationFailedError):
            await generator.answer_question(world, humans, QUESTION)

    @pytest.mark.asyncio
    async def test_empty_answer_is_a_refusal_to_serve(
        self, generator, world, humans, llm
    ):
        llm.text_response = "   "

        with pytest.raises(AdvisorGenerationFailedError):
            await generator.answer_question(world, humans, QUESTION)


# ==================================================================
# ЗАПРОС ДЕЙСТВИЙ ПОСЛЕ ВЫБОРА (ЗАГЛУШКА)
# ==================================================================


class TestRequestActions:
    async def _proposal(self, generator, world, humans, llm, proposal_response):
        llm.structured_response = proposal_response()
        return await generator.generate_proposal(world, humans)

    @pytest.mark.asyncio
    async def test_choice_of_the_player_reaches_the_advisor(
        self, generator, world, humans, llm, proposal_response
    ):
        proposal = await self._proposal(generator, world, humans, llm, proposal_response)
        option = proposal.options[1]

        await generator.request_actions(world, humans, proposal, option)

        assert option.label in llm.text_calls[-1]["user_prompt"]

    @pytest.mark.asyncio
    async def test_player_words_reach_the_advisor(
        self, generator, world, humans, llm, proposal_response
    ):
        """Свободный ответ игрока - тоже часть разговора."""
        proposal = await self._proposal(generator, world, humans, llm, proposal_response)
        freeform = proposal.options[-1]

        await generator.request_actions(
            world, humans, proposal, freeform, player_reply="Налоги не тронь, найди иное."
        )

        assert "Налоги не тронь" in llm.text_calls[-1]["user_prompt"]

    @pytest.mark.asyncio
    async def test_no_actions_until_the_skills_are_written(
        self, generator, world, humans, llm, proposal_response
    ):
        """
        Действовать советник обязан только через навыки Function Calling,
        а их схем пока нет: список намерений всегда пуст.
        """
        proposal = await self._proposal(generator, world, humans, llm, proposal_response)
        llm.text_response = "Будет исполнено, мой лорд."

        reply, actions = await generator.request_actions(
            world, humans, proposal, proposal.options[0]
        )

        assert actions == []
        assert reply == "Будет исполнено, мой лорд."

    @pytest.mark.asyncio
    async def test_broken_model_still_leaves_a_reply(
        self, generator, world, humans, llm, proposal_response
    ):
        """
        Игрок уже нажал кнопку: окно должно закрыться репликой, а не ошибкой.
        """
        proposal = await self._proposal(generator, world, humans, llm, proposal_response)
        llm.error = LLMRequestFailedError("openai", "gpt", "таймаут")

        reply, actions = await generator.request_actions(
            world, humans, proposal, proposal.options[0]
        )

        assert reply
        assert actions == []
