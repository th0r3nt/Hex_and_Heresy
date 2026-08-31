"""
Тесты фасада советника: настройка, пауза между непрошеными советами,
реестр открытых предложений, диалог и реакция на выбор игрока.

Фасад - витрина механики для интерфейса: сам он ничего не генерирует и
ничего не применяет, а решает, когда советнику говорить и что из его
предложений доходит до мира через исполнителя навыков.
"""

import pytest

from src.back.l01_domain.exceptions.advisor import (
    AdvisorDisabledError,
    AdvisorOptionNotFoundError,
    AdvisorProposalNotFoundError,
)
from src.back.l01_domain.exceptions.base import DomainError
from src.back.l01_domain.exceptions.factions import FactionNotFoundError
from src.back.l01_domain.factions.models.advisor import (
    AdvisorActionStatus,
    AdvisorOptionKind,
)
from src.back.l01_domain.llm.tools.definitions.strategic import SET_TAX_RATE
from src.back.l02_services.mechanics.advisor.facade import AdvisorFacade
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.tests.l02_services.fakes import reply, tool_call
from src.back.utils.event.registry import GameEvents

QUESTION = "Что нам выгоднее построить в Железной пади?"

RAISE_TAXES = tool_call("set_tax_rate", rate=1.1)


async def offer(facade, world, llm, proposal_call, **overrides):
    """Готовое открытое предложение фракции игрока."""
    llm.script(reply("", proposal_call(**overrides)))
    return await facade.offer_proposal(world, "humans")


# ==================================================================
# НАСТРОЙКА СОВЕТНИКА
# ==================================================================


class TestSettings:
    @pytest.mark.asyncio
    async def test_disabled_advisor_stays_silent_without_an_error(
        self, facade, world, llm, proposal_call
    ):
        """
        Интерфейс дергает советника каждый такт: выключенная настройка -
        не повод для красного экрана.
        """
        llm.script(reply("", proposal_call()))
        facade.set_enabled(False)

        assert await facade.offer_proposal(world, "humans") is None
        assert llm.calls == []

    @pytest.mark.asyncio
    async def test_disabled_advisor_refuses_a_direct_question(self, facade, world):
        """А вот окно, которого игрок не включал, открывать нечем."""
        facade.set_enabled(False)

        with pytest.raises(AdvisorDisabledError):
            await facade.ask(world, "humans", QUESTION)

    @pytest.mark.asyncio
    async def test_personality_reaches_the_prompt(
        self, facade, world, llm, proposal_call
    ):
        llm.script(reply("", proposal_call()))
        facade.set_personality("humans", "Шаман, говорит загадками.")

        await facade.offer_proposal(world, "humans")

        assert "Шаман, говорит загадками." in llm.calls[0]["system_prompt"]

    @pytest.mark.asyncio
    async def test_unknown_faction_is_rejected_before_the_model(self, facade, world, llm):
        with pytest.raises(FactionNotFoundError):
            await facade.offer_proposal(world, "elfs")

        assert llm.calls == []


# ==================================================================
# ПАУЗА МЕЖДУ СОВЕТАМИ
# ==================================================================


class TestProposalPacing:
    def _facade(self, llm, fake_bus, prompts, contexts) -> AdvisorFacade:
        return AdvisorFacade(
            llm_client=llm,
            prompt_builder=prompts,
            context_builder=contexts,
            event_bus=fake_bus,
            proposal_interval=3,
        )

    @pytest.mark.asyncio
    async def test_advisor_does_not_speak_every_tick(
        self, llm, fake_bus, fake_prompt_builder, fake_context_builder,
        world, proposal_call,
    ):
        """Советник не должен превращаться в назойливое окно каждый ход."""
        facade = self._facade(llm, fake_bus, fake_prompt_builder, fake_context_builder)
        llm.script(reply("", proposal_call()))
        world.time.total_ticks = 10

        assert await facade.offer_proposal(world, "humans") is not None

        world.time.total_ticks = 11
        assert await facade.offer_proposal(world, "humans") is None
        assert len(llm.calls) == 1

    @pytest.mark.asyncio
    async def test_advisor_speaks_again_when_the_pause_is_over(
        self, llm, fake_bus, fake_prompt_builder, fake_context_builder,
        world, proposal_call,
    ):
        facade = self._facade(llm, fake_bus, fake_prompt_builder, fake_context_builder)
        llm.script(reply("", proposal_call()), reply("", proposal_call()))
        world.time.total_ticks = 10
        await facade.offer_proposal(world, "humans")

        world.time.total_ticks = 13

        assert facade.should_offer(world, "humans") is True
        assert await facade.offer_proposal(world, "humans") is not None

    @pytest.mark.asyncio
    async def test_force_ignores_the_pause(
        self, llm, fake_bus, fake_prompt_builder, fake_context_builder,
        world, proposal_call,
    ):
        facade = self._facade(llm, fake_bus, fake_prompt_builder, fake_context_builder)
        llm.script(reply("", proposal_call()), reply("", proposal_call()))
        world.time.total_ticks = 10
        await facade.offer_proposal(world, "humans")

        world.time.total_ticks = 11

        assert await facade.offer_proposal(world, "humans", force=True) is not None


# ==================================================================
# РЕЕСТР ОТКРЫТЫХ ПРЕДЛОЖЕНИЙ
# ==================================================================


class TestPendingProposals:
    @pytest.mark.asyncio
    async def test_offered_proposal_waits_for_the_player(
        self, facade, world, llm, proposal_call
    ):
        """Окно советника переживает перезагрузку интерфейса."""
        proposal = await offer(facade, world, llm, proposal_call)

        assert facade.pending_proposals("humans") == [proposal]
        assert facade.get_proposal(proposal.id) is proposal

    @pytest.mark.asyncio
    async def test_answered_proposal_leaves_the_queue(
        self, facade, world, llm, proposal_call
    ):
        proposal = await offer(facade, world, llm, proposal_call)

        await facade.answer_proposal(world, proposal.id, proposal.options[0].id)

        assert facade.pending_proposals("humans") == []

    @pytest.mark.asyncio
    async def test_silence_leaves_nothing_in_the_queue(self, facade, world, llm):
        llm.script(reply("В державе спокойно."))

        assert await facade.offer_proposal(world, "humans") is None
        assert facade.pending_proposals("humans") == []

    def test_unknown_proposal_is_reported(self, facade):
        with pytest.raises(AdvisorProposalNotFoundError):
            facade.get_proposal("advp_never_was")

    @pytest.mark.asyncio
    async def test_leaving_the_party_forgets_the_advice(
        self, facade, world, llm, proposal_call
    ):
        """Советы прошлой партии новой уже не касаются."""
        await offer(facade, world, llm, proposal_call)

        facade.forget_proposals()

        assert facade.pending_proposals("humans") == []
        assert facade.should_offer(world, "humans") is True

    @pytest.mark.asyncio
    async def test_offered_event_carries_the_advisors_words(
        self, facade, world, llm, fake_bus, proposal_call
    ):
        proposal = await offer(facade, world, llm, proposal_call)

        assert GameEvents.Advisor.PROPOSAL_OFFERED in fake_bus.names()
        payload = fake_bus.payload_of(GameEvents.Advisor.PROPOSAL_OFFERED)
        assert payload["faction_id"] == "humans"
        assert payload["proposal_id"] == proposal.id
        assert payload["message"] == proposal.message


# ==================================================================
# ДИАЛОГОВЫЙ РЕЖИМ
# ==================================================================


class TestDialogue:
    @pytest.mark.asyncio
    async def test_advisor_answers_the_question(self, facade, world, llm):
        llm.text_response = "В Железной пади выгоднее рудник, мой лорд."

        answer = await facade.ask(world, "humans", QUESTION)

        assert answer.faction_id == "humans"
        assert answer.question == QUESTION
        assert answer.text == llm.text_response

    @pytest.mark.asyncio
    async def test_dialogue_does_not_consume_the_pause(
        self, facade, world, llm, proposal_call
    ):
        """
        Вопрос игрока и непрошеный совет живут порознь: спросив совета,
        игрок не должен потерять плановый доклад.
        """
        await facade.ask(world, "humans", QUESTION)

        llm.script(reply("", proposal_call()))
        assert await facade.offer_proposal(world, "humans") is not None


# ==================================================================
# РЕАКЦИЯ НА ВЫБОР ИГРОКА
# ==================================================================


class TestAnswerProposal:
    @pytest.mark.asyncio
    async def test_refusal_closes_the_window_silently(
        self, facade, world, llm, proposal_call
    ):
        """Советника не спрашивают, что он думает по поводу отказа."""
        proposal = await offer(facade, world, llm, proposal_call)
        decline = proposal.options[0]
        decline.kind = AdvisorOptionKind.DECLINE

        decision = await facade.answer_proposal(world, proposal.id, decline.id)

        assert decision.option_id == decline.id
        assert decision.advisor_reply == ""
        assert decision.outcomes == []
        # К модели фасад больше не обращался: единственный вызов - сам совет
        assert len(llm.calls) == 1

    @pytest.mark.asyncio
    async def test_accepted_proposal_gets_the_advisors_reply(
        self, facade, world, llm, proposal_call
    ):
        proposal = await offer(facade, world, llm, proposal_call)
        llm.script(reply("Будет исполнено, мой лорд."))

        decision = await facade.answer_proposal(world, proposal.id, proposal.options[0].id)

        assert decision.advisor_reply == "Будет исполнено, мой лорд."

    @pytest.mark.asyncio
    async def test_without_an_executor_nothing_reaches_the_world(
        self, facade, world, llm, fake_bus, proposal_call
    ):
        """
        Исполнитель навыков фасаду не подключен: советник отвечает словами,
        но до мира его решение не доходит - и интерфейс это видит.
        """
        proposal = await offer(facade, world, llm, proposal_call)
        llm.script(reply("Будет исполнено.", RAISE_TAXES))

        decision = await facade.answer_proposal(world, proposal.id, proposal.options[0].id)

        assert decision.outcomes == []
        assert decision.executed_actions == []
        assert GameEvents.Advisor.ACTION_EXECUTED not in fake_bus.names()

    @pytest.mark.asyncio
    async def test_unknown_option_is_rejected(self, facade, world, llm, proposal_call):
        proposal = await offer(facade, world, llm, proposal_call)

        with pytest.raises(AdvisorOptionNotFoundError):
            await facade.answer_proposal(world, proposal.id, "opt_never_offered")

        assert facade.pending_proposals("humans") == [proposal]

    @pytest.mark.asyncio
    async def test_answered_event_names_the_chosen_button(
        self, facade, world, llm, fake_bus, proposal_call
    ):
        proposal = await offer(facade, world, llm, proposal_call)
        option = proposal.options[1]

        await facade.answer_proposal(world, proposal.id, option.id)

        payload = fake_bus.payload_of(GameEvents.Advisor.PROPOSAL_ANSWERED)
        assert payload["proposal_id"] == proposal.id
        assert payload["option_id"] == option.id
        assert payload["option_label"] == option.label

    @pytest.mark.asyncio
    async def test_disabled_advisor_cannot_be_answered(
        self, facade, world, llm, proposal_call
    ):
        proposal = await offer(facade, world, llm, proposal_call)
        facade.set_enabled(False)

        with pytest.raises(AdvisorDisabledError):
            await facade.answer_proposal(world, proposal.id, proposal.options[0].id)


# ==================================================================
# ИСПОЛНИТЕЛЬ НАВЫКОВ
# ==================================================================


class TestExecutedActions:
    """
    Решение игрока доезжает до мира только через исполнителя навыков:
    фасад отдает ему вызовы советника и рассказывает о сделанном событием.
    """

    def _facade(self, llm, fake_bus, prompts, contexts, executor) -> AdvisorFacade:
        return AdvisorFacade(
            llm_client=llm,
            prompt_builder=prompts,
            context_builder=contexts,
            tool_executor=executor,
            event_bus=fake_bus,
            proposal_interval=0,
        )

    @pytest.mark.asyncio
    async def test_executed_action_is_published(
        self, llm, fake_bus, fake_prompt_builder, fake_context_builder,
        world, proposal_call,
    ):
        executor = ToolExecutor()

        async def raise_taxes(params, ctx) -> str:
            assert ctx.caller_faction_id == "humans"
            return f"Налог поднят до {params.rate}."

        executor.register_handler(SET_TAX_RATE, raise_taxes)

        facade = self._facade(
            llm, fake_bus, fake_prompt_builder, fake_context_builder, executor
        )
        proposal = await offer(facade, world, llm, proposal_call)
        llm.script(reply("Будет исполнено.", RAISE_TAXES))

        decision = await facade.answer_proposal(
            world, proposal.id, proposal.options[0].id
        )

        assert len(decision.executed_actions) == 1
        assert decision.outcomes[0].status == AdvisorActionStatus.EXECUTED
        payload = fake_bus.payload_of(GameEvents.Advisor.ACTION_EXECUTED)
        assert payload["tool_name"] == "set_tax_rate"
        assert payload["detail"] == "Налог поднят до 1.1."

    @pytest.mark.asyncio
    async def test_rejected_action_leaves_the_reason_and_no_event(
        self, llm, fake_bus, fake_prompt_builder, fake_context_builder,
        world, proposal_call,
    ):
        """Мир не принял решение: игрок видит причину, а событие не уходит."""
        executor = ToolExecutor()

        async def refuse(params, ctx) -> str:
            raise DomainError("Казна не выдержит такой ставки.")

        executor.register_handler(SET_TAX_RATE, refuse)

        facade = self._facade(
            llm, fake_bus, fake_prompt_builder, fake_context_builder, executor
        )
        proposal = await offer(facade, world, llm, proposal_call)
        llm.script(reply("Будет исполнено.", RAISE_TAXES))

        decision = await facade.answer_proposal(
            world, proposal.id, proposal.options[0].id
        )

        assert decision.executed_actions == []
        assert decision.outcomes[0].status == AdvisorActionStatus.FAILED
        assert decision.outcomes[0].detail == "Казна не выдержит такой ставки."
        assert GameEvents.Advisor.ACTION_EXECUTED not in fake_bus.names()
