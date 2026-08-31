"""
Тесты разговора с советником: сборка его промпта, разбор вызванных им навыков
и намерения, которые он передает исполнителю.

Генератор - это переводчик между моделью и доменом: он не решает, когда
советнику говорить, но отвечает за то, чтобы окно предложения всегда
соответствовало контракту интерфейса.
"""

import pytest

from src.back.l01_domain.exceptions.advisor import AdvisorGenerationFailedError
from src.back.l01_domain.exceptions.llm import LLMRequestFailedError
from src.back.l01_domain.factions.models.advisor import ADVISOR_MAX_OPTIONS
from src.back.l01_domain.llm.tools.catalog import Toolset, get_toolset
from src.back.l02_services.mechanics.advisor.generation import FREEFORM_OPTION_LABEL
from src.back.tests.l02_services.fakes import reply, tool_call

QUESTION = "Какая армия врага ближе всего к столице?"


# ==================================================================
# СИСТЕМНЫЙ ПРОМПТ СОВЕТНИКА
# ==================================================================


class TestSystemPrompt:
    @pytest.mark.asyncio
    async def test_prompt_carries_role_mechanics_and_race(
        self, generator, world, humans, llm, proposal_call
    ):
        """
        У каждой расы свой советник: в промпт уходят его роль, правила
        экономики и стратегии и лор фракции (см. docs/game_mechanics/advisor.md).
        """
        llm.script(reply("", proposal_call()))

        await generator.generate_proposal(world, humans)

        system_prompt = llm.calls[0]["system_prompt"]
        assert "[base.persona]" in system_prompt
        assert "[base.mechanics.economy]" in system_prompt
        assert "[base.mechanics.strategic]" in system_prompt
        assert "[roles.advisor.prompt]" in system_prompt
        assert "[factions.humans]" in system_prompt
        assert "[lore.basic.medium]" in system_prompt

    @pytest.mark.asyncio
    async def test_prompt_carries_the_current_slice_of_the_world(
        self, generator, world, humans, llm, proposal_call
    ):
        """Советник советует по отчетам, а не вслепую."""
        llm.script(reply("", proposal_call()))

        await generator.generate_proposal(world, humans)

        assert "[advisor]" in llm.calls[0]["system_prompt"]

    @pytest.mark.asyncio
    async def test_custom_personality_reaches_the_prompt(
        self, generator, world, humans, llm, proposal_call
    ):
        """Личность советника пишет игрок или мастер игры - она обязана доехать."""
        llm.script(reply("", proposal_call()))

        await generator.generate_proposal(
            world, humans, personality_prompt="Фанатичный инквизитор, говорит приказами."
        )

        assert "Фанатичный инквизитор" in llm.calls[0]["system_prompt"]

    @pytest.mark.asyncio
    async def test_advisor_gets_only_the_tools_of_his_council(
        self, generator, world, humans, llm, proposal_call
    ):
        """
        Набор навыков привязан к сцене: на докладе правителю советник вправе
        только предложить решение, а не пойти воевать.
        """
        llm.script(reply("", proposal_call()))

        await generator.generate_proposal(world, humans)

        assert llm.calls[0]["tools"] == get_toolset(Toolset.ADVISOR_COUNCIL)


# ==================================================================
# ПАССИВНАЯ ИНИЦИАТИВА
# ==================================================================


class TestGenerateProposal:
    @pytest.mark.asyncio
    async def test_proposal_carries_the_advisors_words(
        self, generator, world, humans, llm, proposal_call
    ):
        call = proposal_call()
        llm.script(reply("", call))

        proposal = await generator.generate_proposal(world, humans)

        assert proposal is not None
        assert proposal.title == call.arguments["title"]
        assert proposal.message == call.arguments["message"]
        assert proposal.faction_id == "humans"

    @pytest.mark.asyncio
    async def test_proposal_remembers_the_tick_it_was_given_on(
        self, generator, world, humans, llm, proposal_call
    ):
        llm.script(reply("", proposal_call()))
        world.time.total_ticks = 17

        proposal = await generator.generate_proposal(world, humans)

        assert proposal.tick == 17

    @pytest.mark.asyncio
    async def test_silent_advisor_does_not_open_a_window(
        self, generator, world, humans, llm
    ):
        """В спокойный такт советник вправе не звать ни одного навыка."""
        llm.script(reply("В державе спокойно."))

        assert await generator.generate_proposal(world, humans) is None

    @pytest.mark.asyncio
    async def test_empty_message_is_treated_as_silence(
        self, generator, world, humans, llm, proposal_call
    ):
        """Окно без текста показывать нечем."""
        llm.script(reply("", proposal_call(message="   ")))

        assert await generator.generate_proposal(world, humans) is None

    @pytest.mark.asyncio
    async def test_broken_arguments_do_not_open_a_window(
        self, generator, world, humans, llm
    ):
        """
        Модель позвала навык, но параметры не по схеме: такой вызов - брак,
        а не повод ронять глобальный такт.
        """
        llm.script(reply("", tool_call("propose_advisor_action", title="Казна пуста")))

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
        self, generator, world, humans, llm, proposal_call
    ):
        llm.script(reply("", proposal_call()))

        proposal = await generator.generate_proposal(world, humans)

        labels = [option.label for option in proposal.options]
        assert labels[:3] == ["Принять", "Поднять на 5%", "Отклонить"]

    @pytest.mark.asyncio
    async def test_freeform_button_is_always_the_last_one(
        self, generator, world, humans, llm, proposal_call
    ):
        """Возразить советнику своими словами игрок вправе всегда."""
        llm.script(reply("", proposal_call()))

        proposal = await generator.generate_proposal(world, humans)

        assert proposal.options[-1].label == FREEFORM_OPTION_LABEL
        assert proposal.options[-1].requires_player_text is True

    @pytest.mark.asyncio
    async def test_model_without_options_gets_the_default_pair(
        self, generator, world, humans, llm, proposal_call
    ):
        """Кнопки без подписей интерфейс заменит на «Принять» и «Отклонить»."""
        llm.script(reply("", proposal_call(options=["   "])))

        proposal = await generator.generate_proposal(world, humans)

        labels = [option.label for option in proposal.options]
        assert labels == ["Принять", "Отклонить", FREEFORM_OPTION_LABEL]

    @pytest.mark.asyncio
    async def test_extra_options_are_cut_to_fit_the_window(
        self, generator, world, humans, llm, proposal_call
    ):
        """Свободный ответ не должен вытесняться болтливостью модели."""
        llm.script(
            reply("", proposal_call(options=[f"Вариант {i}" for i in range(10)]))
        )

        proposal = await generator.generate_proposal(world, humans)

        assert len(proposal.options) == ADVISOR_MAX_OPTIONS
        assert proposal.options[-1].requires_player_text is True

    @pytest.mark.asyncio
    async def test_freeform_option_of_the_model_is_not_duplicated(
        self, generator, world, humans, llm, proposal_call
    ):
        """Модель предложила свободный ответ сама - кнопка все равно одна."""
        llm.script(
            reply("", proposal_call(options=["Принять", FREEFORM_OPTION_LABEL]))
        )

        proposal = await generator.generate_proposal(world, humans)

        labels = [option.label for option in proposal.options]
        assert labels == ["Принять", FREEFORM_OPTION_LABEL]
        assert len([o for o in proposal.options if o.requires_player_text]) == 1


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
# ЗАПРОС ДЕЙСТВИЙ ПОСЛЕ ВЫБОРА
# ==================================================================


class TestRequestActions:
    async def _proposal(self, generator, world, humans, llm, proposal_call):
        llm.script(reply("", proposal_call()))
        return await generator.generate_proposal(world, humans)

    @pytest.mark.asyncio
    async def test_choice_of_the_player_reaches_the_advisor(
        self, generator, world, humans, llm, proposal_call
    ):
        proposal = await self._proposal(generator, world, humans, llm, proposal_call)
        option = proposal.options[1]

        await generator.request_actions(world, humans, proposal, option)

        assert option.label in llm.calls[-1]["user_prompt"]

    @pytest.mark.asyncio
    async def test_player_words_reach_the_advisor(
        self, generator, world, humans, llm, proposal_call
    ):
        """Свободный ответ игрока - тоже часть разговора."""
        proposal = await self._proposal(generator, world, humans, llm, proposal_call)
        freeform = proposal.options[-1]

        await generator.request_actions(
            world, humans, proposal, freeform, player_reply="Налоги не тронь, найди иное."
        )

        assert "Налоги не тронь" in llm.calls[-1]["user_prompt"]

    @pytest.mark.asyncio
    async def test_advisor_acts_through_the_tools_of_his_turn(
        self, generator, world, humans, llm, proposal_call
    ):
        """
        Решение правителя советник исполняет навыками стратегического хода:
        генератор отдает их исполнителю как есть.
        """
        proposal = await self._proposal(generator, world, humans, llm, proposal_call)
        raise_taxes = tool_call("set_tax_rate", rate=1.1)
        llm.script(reply("Будет исполнено, мой лорд.", raise_taxes))

        reply_text, calls = await generator.request_actions(
            world, humans, proposal, proposal.options[0]
        )

        assert reply_text == "Будет исполнено, мой лорд."
        assert calls == [raise_taxes]
        assert llm.calls[-1]["tools"] == get_toolset(Toolset.STRATEGIC_TURN)

    @pytest.mark.asyncio
    async def test_advisor_without_tools_only_speaks(
        self, generator, world, humans, llm, proposal_call
    ):
        """Советник вправе ограничиться словами - до мира ничего не доедет."""
        proposal = await self._proposal(generator, world, humans, llm, proposal_call)
        llm.script(reply("Тогда оставим казну в покое."))

        reply_text, calls = await generator.request_actions(
            world, humans, proposal, proposal.options[0]
        )

        assert reply_text == "Тогда оставим казну в покое."
        assert calls == []

    @pytest.mark.asyncio
    async def test_broken_model_still_leaves_a_reply(
        self, generator, world, humans, llm, proposal_call
    ):
        """
        Игрок уже нажал кнопку: окно должно закрыться репликой, а не ошибкой.
        """
        proposal = await self._proposal(generator, world, humans, llm, proposal_call)
        llm.error = LLMRequestFailedError("openai", "gpt", "таймаут")

        reply_text, calls = await generator.request_actions(
            world, humans, proposal, proposal.options[0]
        )

        assert reply_text
        assert calls == []
