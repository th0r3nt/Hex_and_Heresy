"""
Тесты переговоров: перенос решений лорда на агрегат отношений,
ответ на депешу, автоматический торг двух нейросетей и казнь посла.
"""

from typing import Optional

import pytest
from pydantic import BaseModel

from src.back.l01_domain.exceptions import AmbassadorUnavailableError
from src.back.l01_domain.factions.constants import (
    DiplomaticActionType,
    DiplomaticStance,
    NegotiationMode,
    ResourceType,
)
from src.back.l01_domain.factions.models.diplomacy.messengers import Dispatch
from src.back.l01_domain.factions.models.diplomacy.negotiations import (
    DiplomaticAction,
    LLMDiplomaticResponse,
)
from src.back.l02_services.mechanics.diplomacy.facade import DiplomacyFacade
from src.back.l02_services.mechanics.diplomacy.negotiations import NegotiationService
from src.back.utils.event.registry import GameEvents


class FakeLLMClient:
    """
    Фейковый LLM: отдает заранее уложенные ответы по очереди.
    Структурированные ответы берутся из structured_replies, свободный
    текст - из text_replies.
    """

    def __init__(
        self,
        structured_replies: Optional[list[BaseModel]] = None,
        text_replies: Optional[list[str]] = None,
    ) -> None:
        self.structured_replies = list(structured_replies or [])
        self.text_replies = list(text_replies or [])
        self.calls: list[tuple[str, str]] = []

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> str:
        self.calls.append((system_prompt, user_prompt))
        if not self.text_replies:
            return "..."
        return self.text_replies.pop(0)

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        temperature: float = 0.6,
    ) -> BaseModel:
        self.calls.append((system_prompt, user_prompt))
        if not self.structured_replies:
            raise AssertionError("FakeLLMClient: структурированные ответы закончились")
        return self.structured_replies.pop(0)


def _reply(text: str, action: Optional[DiplomaticAction] = None) -> LLMDiplomaticResponse:
    return LLMDiplomaticResponse(reply_text=text, action=action)


class TestApplyAction:
    @pytest.mark.asyncio
    async def test_trade_action_creates_agreement(self, world, fake_bus):
        service = NegotiationService(llm_client=FakeLLMClient(), event_bus=fake_bus)

        applied = await service.apply_action(
            world,
            "humans",
            "elfs",
            DiplomaticAction(
                kind=DiplomaticActionType.PROPOSE_TRADE,
                give_resource=ResourceType.FOOD,
                give_amount=50.0,
                get_resource=ResourceType.GOLD,
                get_amount=30.0,
                duration_turns=4,
            ),
        )

        relation = world.get_relation("humans", "elfs")
        assert applied is True
        assert relation.trade_agreement.give_amount == 50.0
        assert relation.trade_agreement.remaining_turns == 4
        assert GameEvents.Diplomacy.TRADE_AGREED in fake_bus.names()

    @pytest.mark.asyncio
    async def test_war_and_peace_switch_stance(self, world):
        service = NegotiationService(llm_client=FakeLLMClient())

        await service.apply_action(
            world, "humans", "elfs", DiplomaticAction(kind=DiplomaticActionType.DECLARE_WAR)
        )
        relation = world.get_relation("humans", "elfs")
        assert relation.stance == DiplomaticStance.WAR

        await service.apply_action(
            world, "humans", "elfs", DiplomaticAction(kind=DiplomaticActionType.MAKE_PEACE)
        )
        assert relation.stance == DiplomaticStance.PEACE

    @pytest.mark.asyncio
    async def test_right_of_passage_goes_to_initiator(self, world):
        service = NegotiationService(llm_client=FakeLLMClient())

        await service.apply_action(
            world,
            "humans",
            "elfs",
            DiplomaticAction(
                kind=DiplomaticActionType.ESTABLISH_RIGHT_OF_PASSAGE,
                gold_amount=500.0,
                duration_turns=3,
                allowed_hex_ids=["hex_1", "hex_2"],
            ),
        )

        passage = world.get_relation("humans", "elfs").right_of_passage
        assert passage.beneficiary_faction_id == "humans"
        assert passage.toll_gold_per_crossing == 500.0
        assert passage.allowed_hex_ids == ["hex_1", "hex_2"]

    @pytest.mark.asyncio
    async def test_tribute_demand_is_recorded(self, world, fake_bus):
        service = NegotiationService(llm_client=FakeLLMClient(), event_bus=fake_bus)

        await service.apply_action(
            world,
            "humans",
            "elfs",
            DiplomaticAction(kind=DiplomaticActionType.DEMAND_TRIBUTE, gold_amount=250.0),
        )

        assert world.get_relation("humans", "elfs").tribute_demanded_gold == 250.0
        assert GameEvents.Diplomacy.TRIBUTE_DEMANDED in fake_bus.names()

    @pytest.mark.asyncio
    async def test_empty_action_changes_nothing(self, world):
        service = NegotiationService(llm_client=FakeLLMClient())

        assert await service.apply_action(world, "humans", "elfs", None) is False
        assert (
            await service.apply_action(
                world, "humans", "elfs", DiplomaticAction(kind=DiplomaticActionType.NONE)
            )
            is False
        )

    @pytest.mark.asyncio
    async def test_incomplete_trade_action_is_ignored(self, world):
        service = NegotiationService(llm_client=FakeLLMClient())

        applied = await service.apply_action(
            world,
            "humans",
            "elfs",
            DiplomaticAction(kind=DiplomaticActionType.PROPOSE_TRADE, give_amount=10.0),
        )

        assert applied is False
        assert world.get_relation("humans", "elfs").trade_agreement is None


class TestDispatchAnswer:
    @pytest.mark.asyncio
    async def test_lord_answers_letter_and_declares_war(
        self, world, fake_bus, fake_prompt_builder
    ):
        llm = FakeLLMClient(
            structured_replies=[
                _reply(
                    "Твои слова оскорбительны. Готовь стены.",
                    DiplomaticAction(kind=DiplomaticActionType.DECLARE_WAR),
                )
            ]
        )
        service = NegotiationService(
            llm_client=llm, event_bus=fake_bus, prompt_builder=fake_prompt_builder
        )
        dispatch = Dispatch(
            sender_faction_id="humans",
            recipient_faction_id="elfs",
            message_text="Уберите своих сборщиков податей.",
        )

        response = await service.answer_dispatch(world, dispatch)

        assert "оскорбительны" in response.reply_text
        assert world.get_relation("humans", "elfs").stance == DiplomaticStance.WAR

        system_prompt, user_prompt = llm.calls[0]
        # Проверяем, что в системный промпт лорда ушли правильные блоки файлов:
        assert "[base/persona.md]" in system_prompt
        assert "[roles/lord.md]" in system_prompt
        assert "[factions/elfs.md]" in system_prompt
        assert "Уберите своих сборщиков податей." in user_prompt


class TestAutoNegotiation:
    @pytest.mark.asyncio
    async def test_dialogue_stops_on_first_decision(self, world, fake_bus):
        llm = FakeLLMClient(
            structured_replies=[
                _reply("Пятьсот золота? Ты смеешься надо мной."),
                _reply(
                    "Восемьсот - и мои дозоры вас не тронут.",
                    DiplomaticAction(
                        kind=DiplomaticActionType.ESTABLISH_RIGHT_OF_PASSAGE,
                        gold_amount=800.0,
                        duration_turns=5,
                    ),
                ),
                _reply("Этой реплики уже быть не должно."),
            ],
            text_replies=[
                "Мой лорд предлагает пятьсот золота за право прохода.",
                "Хорошо, восемьсот - но это последнее слово.",
            ],
        )
        facade = DiplomacyFacade(llm_client=llm, event_bus=fake_bus)
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
        # Третий заготовленный ответ не понадобился - диалог оборвался на решении
        assert len(llm.structured_replies) == 1

    @pytest.mark.asyncio
    async def test_executed_ambassador_dies_and_war_begins(self, world, fake_bus):
        llm = FakeLLMClient(
            structured_replies=[
                _reply(
                    "Многа букав. Я иду ломать твоя замок!",
                    DiplomaticAction(kind=DiplomaticActionType.EXECUTE_AMBASSADOR),
                )
            ]
        )
        facade = DiplomacyFacade(llm_client=llm, event_bus=fake_bus)
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
        facade = DiplomacyFacade(llm_client=FakeLLMClient())
        ambassador = await facade.send_ambassador(world, "humans", "Граф Вальтер", "elfs")

        with pytest.raises(AmbassadorUnavailableError):
            await facade.speak_to_lord(world, ambassador.id, "Мы уже пришли?")

    @pytest.mark.asyncio
    async def test_negotiations_require_llm_client(self, world):
        facade = DiplomacyFacade()
        ambassador = await facade.send_ambassador(world, "humans", "Граф Вальтер", "elfs")

        with pytest.raises(ValueError):
            await facade.run_auto_negotiation(world, ambassador.id)
