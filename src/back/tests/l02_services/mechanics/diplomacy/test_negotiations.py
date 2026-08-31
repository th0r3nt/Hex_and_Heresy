"""
Тесты переговоров: перенос решений лорда на агрегат отношений через навыки,
ответ на депешу, автоматический торг двух нейросетей и казнь посла.

Лорд говорит с миром только вызовами навыков (Function Calling): слова
приезжают текстом, а любое действие - через ToolExecutor и его обработчики.
"""

from typing import Any

import pytest

from src.back.l01_domain.exceptions.diplomacy import AmbassadorUnavailableError
from src.back.l01_domain.factions.constants import (
    DiplomaticStance,
    NegotiationMode,
    ResourceType,
)
from src.back.l01_domain.factions.models.diplomacy.messengers import Dispatch
from src.back.l01_domain.llm.models.tools import ToolCall, ToolDefinition
from src.back.l02_services.mechanics.diplomacy.facade import DiplomacyFacade
from src.back.l02_services.mechanics.diplomacy.negotiations import NegotiationService
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.l02_services.mechanics.tools.handlers import (
    DiplomacyToolHandlers,
    GeneralToolHandlers,
)
from src.back.tests.l02_services.fakes import (
    FakeContextBuilder,
    FakePromptBuilder,
    LLMReply,
    reply,
    tool_call,
)
from src.back.utils.event.registry import GameEvents


class FakeLLMClient:
    """
    Фейковый LLM: отдает заранее уложенные ответы по очереди.

    Один ответ - это свободный текст лорда или посла плюс навыки, которые он
    решил вызвать. Когда очередь кончилась, модель молчит без вызовов.
    """

    def __init__(self, *replies: LLMReply) -> None:
        self.replies: list[LLMReply] = list(replies)
        self.calls: list[tuple[str, str]] = []

    async def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
        temperature: float = 0.6,
        tool_choice: Any = "auto",
    ) -> tuple[str, list[ToolCall]]:
        self.calls.append((system_prompt, user_prompt))
        if not self.replies:
            return "", []
        content, calls = self.replies.pop(0)
        return content, list(calls)


def _executor(facade: DiplomacyFacade) -> ToolExecutor:
    """Исполнитель с навыками аудиенции, подключенными к фасаду дипломатии."""
    executor = ToolExecutor()
    GeneralToolHandlers().register(executor)
    DiplomacyToolHandlers(facade).register(executor)
    return executor


def _service(llm, event_bus=None, tool_executor=None) -> NegotiationService:
    """Сервис переговоров на доменных фейках сборщиков."""
    return NegotiationService(
        llm_client=llm,
        prompt_builder=FakePromptBuilder(),
        context_builder=FakeContextBuilder(),
        tool_executor=tool_executor,
        event_bus=event_bus,
    )


def _facade(llm=None, event_bus=None, with_tools: bool = False) -> DiplomacyFacade:
    """
    Фасад дипломатии: сборщики нужны только вместе с моделью.

    with_tools подключает переговорам исполнителя навыков - так же, как это
    делает корень компоновки в main.py.
    """
    facade = DiplomacyFacade(
        llm_client=llm,
        prompt_builder=FakePromptBuilder() if llm is not None else None,
        context_builder=FakeContextBuilder() if llm is not None else None,
        event_bus=event_bus,
    )
    if with_tools and facade._negotiations is not None:
        facade._negotiations.set_tool_executor(_executor(facade))
    return facade


def _audience_context(world, host: str = "elfs", guest: str = "humans"):
    """Контекст тронного зала: решение принимает хозяин, проситель - гость."""
    return ToolExecutionContext(
        world_state=world,
        caller_faction_id=host,
        target_faction_id=guest,
    )


# ==================================================================
# РЕШЕНИЯ ЛОРДА ЧЕРЕЗ НАВЫКИ
# ==================================================================


class TestToolActions:
    """Навык лорда обязан доехать до агрегата отношений и до шины событий."""

    @pytest.mark.asyncio
    async def test_trade_action_creates_agreement(self, world, fake_bus):
        executor = _executor(_facade(event_bus=fake_bus))

        result = await executor.execute(
            tool_call(
                "propose_trade",
                give_resource=ResourceType.FOOD.value,
                give_amount=50.0,
                get_resource=ResourceType.GOLD.value,
                get_amount=30.0,
                duration_turns=4,
            ),
            _audience_context(world),
        )

        relation = world.get_relation("humans", "elfs")
        assert result.success is True
        assert relation.trade_agreement.give_amount == 50.0
        assert relation.trade_agreement.remaining_turns == 4
        assert GameEvents.Diplomacy.TRADE_AGREED in fake_bus.names()

    @pytest.mark.asyncio
    async def test_war_and_peace_switch_stance(self, world):
        executor = _executor(_facade())
        context = _audience_context(world)

        await executor.execute(tool_call("declare_war"), context)
        relation = world.get_relation("humans", "elfs")
        assert relation.stance == DiplomaticStance.WAR

        await executor.execute(tool_call("make_peace"), context)
        assert relation.stance == DiplomaticStance.PEACE

    @pytest.mark.asyncio
    async def test_right_of_passage_goes_to_the_guest(self, world):
        """Право прохода дает хозяин земель гостю, а не себе."""
        executor = _executor(_facade())

        await executor.execute(
            tool_call(
                "establish_right_of_passage",
                toll_gold_per_crossing=500.0,
                duration_turns=3,
                allowed_hex_ids=["hex_1", "hex_2"],
            ),
            _audience_context(world),
        )

        passage = world.get_relation("humans", "elfs").right_of_passage
        assert passage.beneficiary_faction_id == "humans"
        assert passage.toll_gold_per_crossing == 500.0
        assert passage.allowed_hex_ids == ["hex_1", "hex_2"]

    @pytest.mark.asyncio
    async def test_tribute_demand_is_recorded(self, world, fake_bus):
        executor = _executor(_facade(event_bus=fake_bus))

        await executor.execute(
            tool_call("demand_tribute", gold_amount=250.0),
            _audience_context(world),
        )

        assert world.get_relation("humans", "elfs").tribute_demanded_gold == 250.0
        assert GameEvents.Diplomacy.TRIBUTE_DEMANDED in fake_bus.names()

    @pytest.mark.asyncio
    async def test_unknown_tool_changes_nothing(self, world):
        """Навык, которого нет в реестре, до мира не доходит."""
        executor = _executor(_facade())

        result = await executor.execute(
            tool_call("annex_everything"), _audience_context(world)
        )

        assert result.success is False
        # Обработчик не отработал, поэтому и отношения между державами не заведены
        assert world.get_relation("humans", "elfs") is None

    @pytest.mark.asyncio
    async def test_incomplete_trade_action_is_ignored(self, world):
        """Половина условий сделки - это не сделка, а брак вызова."""
        executor = _executor(_facade())

        result = await executor.execute(
            tool_call("propose_trade", give_amount=10.0),
            _audience_context(world),
        )

        assert result.success is False
        assert world.get_relation("humans", "elfs") is None


# ==================================================================
# ОТВЕТ НА ДЕПЕШУ
# ==================================================================


class TestDispatchAnswer:
    def _dispatch(self) -> Dispatch:
        return Dispatch(
            sender_faction_id="humans",
            recipient_faction_id="elfs",
            message_text="Уберите своих сборщиков податей.",
        )

    @pytest.mark.asyncio
    async def test_lord_answers_letter_and_declares_war(self, world, fake_bus):
        llm = FakeLLMClient(
            reply(
                "Твои слова оскорбительны. Готовь стены.",
                tool_call("declare_war", reason="оскорбление послов"),
            )
        )
        facade = _facade(event_bus=fake_bus)
        service = _service(llm, fake_bus, tool_executor=_executor(facade))

        response = await service.answer_dispatch(world, self._dispatch())

        assert "оскорбительны" in response.reply_text
        assert world.get_relation("humans", "elfs").stance == DiplomaticStance.WAR

        system_prompt, user_prompt = llm.calls[0]
        # Проверяем, что в системный промпт лорда ушли правильные блоки файлов:
        assert "[base.persona]" in system_prompt
        assert "[roles.lord.prompt]" in system_prompt
        assert "[factions.elfs]" in system_prompt
        assert "Уберите своих сборщиков податей." in user_prompt

    @pytest.mark.asyncio
    async def test_words_of_the_reply_tool_reach_the_player(self, world, fake_bus):
        """Лорд вправе ответить навыком свободной речи - это его реплика."""
        llm = FakeLLMClient(
            reply("", tool_call("reply", text="Мои сборщики стоят на моей земле."))
        )
        facade = _facade(event_bus=fake_bus)
        service = _service(llm, fake_bus, tool_executor=_executor(facade))

        response = await service.answer_dispatch(world, self._dispatch())

        assert response.reply_text == "Мои сборщики стоят на моей земле."
        assert response.action is None

    @pytest.mark.asyncio
    async def test_without_an_executor_the_world_stays_untouched(self, world, fake_bus):
        """Без исполнителя навыков лорд остается при своих словах."""
        llm = FakeLLMClient(reply("Готовь стены.", tool_call("declare_war")))
        service = _service(llm, fake_bus)

        response = await service.answer_dispatch(world, self._dispatch())

        assert response.reply_text == "Готовь стены."
        assert response.action is None
        assert world.get_relation("humans", "elfs") is None


# ==================================================================
# АВТОМАТИЧЕСКИЙ ТОРГ И СУДЬБА ПОСЛА
# ==================================================================


class TestAutoNegotiation:
    @pytest.mark.asyncio
    async def test_dialogue_stops_on_first_decision(self, world, fake_bus):
        llm = FakeLLMClient(
            reply("Мой лорд предлагает пятьсот золота за право прохода."),
            reply("Пятьсот золота? Ты смеешься надо мной."),
            reply("Хорошо, восемьсот - но это последнее слово."),
            reply(
                "Восемьсот - и мои дозоры вас не тронут.",
                tool_call(
                    "establish_right_of_passage",
                    toll_gold_per_crossing=800.0,
                    duration_turns=5,
                ),
            ),
            reply("Этой реплики уже быть не должно."),
        )
        facade = _facade(llm, fake_bus, with_tools=True)
        ambassador = await facade.send_ambassador(
            world,
            faction_id="humans",
            name="Граф Вальтер",
            target_faction_id="elfs",
            negotiation_mode=NegotiationMode.AUTOMATIC,
            directive="Выторгуй право прохода за 500 золота, торгуйся до 800.",
        )
        for _ in range(4):
            await facade.process_tick(world)

        transcript = await facade.run_auto_negotiation(world, ambassador.id)

        assert [line.speaker for line in transcript.lines] == [
            "ambassador",
            "lord",
            "ambassador",
            "lord",
        ]
        passage = world.get_relation("humans", "elfs").right_of_passage
        assert passage.toll_gold_per_crossing == 800.0
        assert passage.beneficiary_faction_id == "humans"
        # Пятый заготовленный ответ не понадобился - диалог оборвался на решении
        assert len(llm.replies) == 1

    @pytest.mark.asyncio
    async def test_executed_ambassador_dies_and_war_begins(self, world, fake_bus):
        llm = FakeLLMClient(
            reply(
                "Многа букав. Я иду ломать твоя замок!",
                tool_call("execute_ambassador", reason="послы людей надоели"),
            )
        )
        facade = _facade(llm, fake_bus, with_tools=True)
        ambassador = await facade.send_ambassador(
            world, "humans", "Граф Вальтер", "elfs", negotiation_mode=NegotiationMode.MANUAL
        )
        for _ in range(4):
            await facade.process_tick(world)

        await facade.speak_to_lord(world, ambassador.id, "Ваше высочество, я привез дары.")

        assert world.ambassadors == []
        assert world.get_relation("humans", "elfs").stance == DiplomaticStance.WAR
        assert GameEvents.Diplomacy.AMBASSADOR_EXECUTED in fake_bus.names()

    @pytest.mark.asyncio
    async def test_ambassador_in_transit_cannot_negotiate(self, world):
        facade = _facade(FakeLLMClient())
        ambassador = await facade.send_ambassador(world, "humans", "Граф Вальтер", "elfs")

        with pytest.raises(AmbassadorUnavailableError):
            await facade.speak_to_lord(world, ambassador.id, "Мы уже пришли?")

    @pytest.mark.asyncio
    async def test_negotiations_require_llm_client(self, world):
        facade = _facade()
        ambassador = await facade.send_ambassador(world, "humans", "Граф Вальтер", "elfs")

        with pytest.raises(ValueError):
            await facade.run_auto_negotiation(world, ambassador.id)

    def test_llm_client_without_builders_is_rejected(self):
        """Сборку графа зависимостей делает корень компоновки, а не фасад."""
        with pytest.raises(ValueError):
            DiplomacyFacade(llm_client=FakeLLMClient())
