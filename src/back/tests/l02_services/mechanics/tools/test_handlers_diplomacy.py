"""
Интеграционные тесты дипломатических навыков: решение лорда обязано доехать
до агрегата отношений, а внешняя политика - до фасада дипломатии.

Сам разговор с моделью проверяется в tests/l02_services/mechanics/diplomacy/
- здесь только исполнение того, что модель уже решила.
"""

import pytest

from src.back.l01_domain.factions.constants import (
    AmbassadorStatus,
    DiplomaticStance,
    NegotiationMode,
    ResourceType,
)
from src.back.tests.l02_services.fakes import tool_call
from src.back.utils.event.registry import GameEvents


@pytest.fixture
def audience(context):
    """
    Контекст тронного зала: решение принимает хозяин, проситель - гость.
    """

    def _audience(host: str = "elfs", guest: str = "humans", **overrides):
        return context(caller_faction_id=host, target_faction_id=guest, **overrides)

    return _audience


async def _ambassador_in_audience(diplomacy_facade, world, mode=NegotiationMode.MANUAL):
    """Доводит посла людей до тронного зала эльфов."""
    ambassador = await diplomacy_facade.send_ambassador(
        world,
        faction_id="humans",
        name="Граф Вальтер",
        target_faction_id="elfs",
        negotiation_mode=mode,
    )
    for _ in range(4):
        await diplomacy_facade.process_tick(world)
    assert ambassador.status == AmbassadorStatus.IN_AUDIENCE
    return ambassador


# ==================================================================
# РЕШЕНИЯ ЛОРДА НА АУДИЕНЦИИ
# ==================================================================


class TestVerdicts:
    async def test_trade_action_creates_agreement(
        self, executor, world, fake_bus, audience
    ):
        result = await executor.execute(
            tool_call(
                "propose_trade",
                give_resource=ResourceType.FOOD.value,
                give_amount=50.0,
                get_resource=ResourceType.GOLD.value,
                get_amount=30.0,
                duration_turns=4,
            ),
            audience(),
        )

        relation = world.get_relation("humans", "elfs")
        assert result.success is True
        assert relation.trade_agreement.give_amount == 50.0
        assert relation.trade_agreement.remaining_turns == 4
        assert GameEvents.Diplomacy.TRADE_AGREED in fake_bus.names()

    async def test_war_and_peace_switch_stance(self, executor, world, audience):
        context = audience()

        await executor.execute(tool_call("declare_war"), context)
        relation = world.get_relation("humans", "elfs")
        assert relation.stance == DiplomaticStance.WAR

        await executor.execute(tool_call("make_peace"), context)
        assert relation.stance == DiplomaticStance.PEACE

    async def test_borders_pact_lists_the_agreed_hexes(self, executor, world, audience):
        await executor.execute(
            tool_call("establish_borders", allowed_hex_ids=["hex_1", "hex_2"]),
            audience(),
        )

        pact = world.get_relation("humans", "elfs").non_aggression_pact
        assert pact.allowed_hex_ids == ["hex_1", "hex_2"]

    async def test_right_of_passage_goes_to_the_guest(self, executor, world, audience):
        """Право прохода дает хозяин земель гостю, а не себе."""
        await executor.execute(
            tool_call(
                "establish_right_of_passage",
                toll_gold_per_crossing=500.0,
                duration_turns=3,
                allowed_hex_ids=["hex_1", "hex_2"],
            ),
            audience(),
        )

        passage = world.get_relation("humans", "elfs").right_of_passage
        assert passage.beneficiary_faction_id == "humans"
        assert passage.toll_gold_per_crossing == 500.0
        assert passage.allowed_hex_ids == ["hex_1", "hex_2"]

    async def test_tribute_demand_is_recorded(self, executor, world, fake_bus, audience):
        await executor.execute(
            tool_call("demand_tribute", gold_amount=250.0), audience()
        )

        assert world.get_relation("humans", "elfs").tribute_demanded_gold == 250.0
        assert GameEvents.Diplomacy.TRIBUTE_DEMANDED in fake_bus.names()

    async def test_pact_during_war_is_refused_by_the_domain(
        self, executor, world, audience
    ):
        """
        Правила игры запрещают торговать во время войны: отказ приезжает от
        домена и достается модели причиной, а не падением сервера.
        """
        context = audience()
        await executor.execute(tool_call("declare_war"), context)

        result = await executor.execute(
            tool_call(
                "propose_trade",
                give_resource=ResourceType.FOOD.value,
                give_amount=10.0,
                get_resource=ResourceType.GOLD.value,
                get_amount=10.0,
            ),
            context,
        )

        assert result.success is False
        assert world.get_relation("humans", "elfs").trade_agreement is None

    async def test_verdict_without_a_counterpart_is_refused(self, executor, world, context):
        """Объявить войну некому: сцена не назвала собеседника."""
        result = await executor.execute(tool_call("declare_war"), context())

        assert result.success is False
        assert world.get_relation("humans", "elfs") is None


# ==================================================================
# ВНЕШНЯЯ ПОЛИТИКА СВОЕГО ХОДА
# ==================================================================


class TestForeignPolicy:
    async def test_dispatch_is_sent_and_paid_for(self, executor, world, context):
        gold_before = world.get_faction("humans").resources[ResourceType.GOLD]

        result = await executor.execute(
            tool_call(
                "send_dispatch",
                recipient_faction_id="elfs",
                message_text="Уберите своих сборщиков податей.",
            ),
            context(),
        )

        assert result.success is True
        assert len(world.dispatches) == 1
        assert world.dispatches[0].message_text == "Уберите своих сборщиков податей."
        assert world.get_faction("humans").resources[ResourceType.GOLD] < gold_before

    async def test_dispatch_to_oneself_is_refused(self, executor, world, context):
        result = await executor.execute(
            tool_call("send_dispatch", recipient_faction_id="humans", message_text="Эй."),
            context(),
        )

        assert result.success is False
        assert world.dispatches == []

    async def test_ambassador_leaves_for_the_foreign_court(self, executor, world, context):
        result = await executor.execute(
            tool_call(
                "send_ambassador",
                name="Граф Вальтер",
                target_faction_id="elfs",
                negotiation_mode=NegotiationMode.AUTOMATIC.value,
                directive="Выторгуй право прохода.",
            ),
            context(),
        )

        assert result.success is True
        assert [amb.name for amb in world.ambassadors] == ["Граф Вальтер"]
        assert world.ambassadors[0].directive == "Выторгуй право прохода."

    async def test_recalled_ambassador_goes_home(
        self, executor, world, diplomacy_facade, context
    ):
        ambassador = await _ambassador_in_audience(diplomacy_facade, world)

        result = await executor.execute(
            tool_call("recall_ambassador", ambassador_id=ambassador.id), context()
        )

        assert result.success is True
        assert ambassador.status != AmbassadorStatus.IN_AUDIENCE

    async def test_tribute_is_paid_out_of_the_treasury(self, executor, world, audience):
        await executor.execute(
            tool_call("demand_tribute", gold_amount=200.0), audience()
        )
        humans_gold = world.get_faction("humans").resources[ResourceType.GOLD]
        elfs_gold = world.get_faction("elfs").resources[ResourceType.GOLD]

        result = await executor.execute(
            tool_call("pay_tribute", receiver_faction_id="elfs"),
            audience(host="humans", guest="elfs"),
        )

        assert result.success is True
        assert result.data["amount_gold"] == 200.0
        assert world.get_faction("humans").resources[ResourceType.GOLD] == humans_gold - 200.0
        assert world.get_faction("elfs").resources[ResourceType.GOLD] == elfs_gold + 200.0
        assert world.get_relation("humans", "elfs").tribute_demanded_gold is None


# ==================================================================
# КАЗНЬ ПОСЛА
# ==================================================================


class TestExecuteAmbassador:
    async def test_executed_ambassador_dies_and_war_begins(
        self, executor, world, diplomacy_facade, fake_bus, audience
    ):
        """
        Казнят того посла, который стоит на этой самой аудиенции: он приезжает
        в контексте актором.
        """
        ambassador = await _ambassador_in_audience(diplomacy_facade, world)

        result = await executor.execute(
            tool_call("execute_ambassador", reason="послы людей надоели"),
            audience(actor_id=ambassador.id),
        )

        assert result.success is True
        assert world.ambassadors == []
        assert world.get_relation("humans", "elfs").stance == DiplomaticStance.WAR
        assert GameEvents.Diplomacy.AMBASSADOR_EXECUTED in fake_bus.names()

    async def test_execution_without_an_ambassador_is_refused(
        self, executor, world, audience
    ):
        result = await executor.execute(tool_call("execute_ambassador"), audience())

        assert result.success is False
        assert "actor_id" in result.error
