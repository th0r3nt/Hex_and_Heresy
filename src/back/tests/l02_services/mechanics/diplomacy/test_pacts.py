"""
Тесты исполнения пактов на такте: переливы по торговому договору,
дань вассала, истечение сроков и разрыв при неисполнении обязательств.
"""

import pytest

from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.diplomacy.pacts import (
    RightOfPassagePact,
    TradeAgreement,
    VassalPact,
    WarAlliancePact,
)
from src.back.l02_services.mechanics.diplomacy.pacts import PactUpkeepService
from src.back.utils.event.registry import GameEvents


@pytest.fixture
def relation(world):
    return world.get_or_create_relation("humans", "elfs")


class TestTradeAgreement:
    @pytest.mark.asyncio
    async def test_resources_flow_both_ways_each_tick(self, world, humans, elfs, relation):
        relation.propose_trade(
            TradeAgreement(
                give_resource=ResourceType.FOOD,
                give_amount=50.0,
                get_resource=ResourceType.GOLD,
                get_amount=30.0,
                duration_turns=3,
                remaining_turns=3,
            )
        )
        humans_food = humans.resources[ResourceType.FOOD]
        elfs_gold = elfs.resources[ResourceType.GOLD]

        closed = await PactUpkeepService().process_tick(world)

        assert closed == []
        assert humans.resources[ResourceType.FOOD] == humans_food - 50.0
        assert elfs.resources[ResourceType.FOOD] == 550.0
        assert elfs.resources[ResourceType.GOLD] == elfs_gold - 30.0
        assert humans.resources[ResourceType.GOLD] == 1030.0
        assert relation.trade_agreement.remaining_turns == 2

    @pytest.mark.asyncio
    async def test_agreement_expires_when_term_runs_out(self, world, relation, fake_bus):
        relation.propose_trade(
            TradeAgreement(
                give_resource=ResourceType.FOOD,
                give_amount=10.0,
                get_resource=ResourceType.GOLD,
                get_amount=10.0,
                duration_turns=1,
                remaining_turns=1,
            )
        )

        closed = await PactUpkeepService(event_bus=fake_bus).process_tick(world)

        assert closed == ["humans:elfs:trade_agreement"]
        assert relation.trade_agreement is None
        assert GameEvents.Diplomacy.PACT_BROKEN in fake_bus.names()

    @pytest.mark.asyncio
    async def test_agreement_breaks_if_side_cannot_pay(self, world, humans, relation):
        humans.resources[ResourceType.FOOD] = 0.0
        relation.propose_trade(
            TradeAgreement(
                give_resource=ResourceType.FOOD,
                give_amount=50.0,
                get_resource=ResourceType.GOLD,
                get_amount=30.0,
                duration_turns=5,
                remaining_turns=5,
            )
        )

        closed = await PactUpkeepService().process_tick(world)

        assert closed == ["humans:elfs:trade_agreement"]
        assert relation.trade_agreement is None
        # Ни одна сторона не платит по разорванному договору
        assert humans.resources[ResourceType.GOLD] == 1000.0


class TestVassalage:
    @pytest.mark.asyncio
    async def test_vassal_pays_tribute_every_tick(
        self, world, humans, elfs, relation, fake_bus
    ):
        relation.form_vassalage(
            VassalPact(
                overlord_faction_id="humans",
                vassal_faction_id="elfs",
                tribute_gold_per_turn=100.0,
            )
        )

        await PactUpkeepService(event_bus=fake_bus).process_tick(world)

        assert elfs.resources[ResourceType.GOLD] == 900.0
        assert humans.resources[ResourceType.GOLD] == 1100.0
        assert GameEvents.Diplomacy.TRIBUTE_PAID in fake_bus.names()

    @pytest.mark.asyncio
    async def test_unpaid_tribute_breaks_vassalage(self, world, elfs, relation):
        elfs.resources[ResourceType.GOLD] = 10.0
        relation.form_vassalage(
            VassalPact(
                overlord_faction_id="humans",
                vassal_faction_id="elfs",
                tribute_gold_per_turn=100.0,
            )
        )

        closed = await PactUpkeepService().process_tick(world)

        assert closed == ["humans:elfs:vassal_pact"]
        assert relation.vassal_pact is None
        assert elfs.resources[ResourceType.GOLD] == 10.0


class TestTimedPacts:
    @pytest.mark.asyncio
    async def test_right_of_passage_and_alliance_count_down(self, world, relation):
        relation.establish_right_of_passage(
            RightOfPassagePact(
                beneficiary_faction_id="humans", duration_turns=2, remaining_turns=2
            )
        )
        relation.form_war_alliance(
            WarAlliancePact(
                common_enemy_faction_id="greenskins",
                loot_split_ratio_a=0.5,
                duration_turns=2,
                remaining_turns=2,
            )
        )
        service = PactUpkeepService()

        assert await service.process_tick(world) == []
        assert relation.right_of_passage.remaining_turns == 1
        assert relation.war_alliance.remaining_turns == 1

        closed = await service.process_tick(world)

        assert closed == [
            "humans:elfs:right_of_passage",
            "humans:elfs:war_alliance",
        ]
        assert relation.right_of_passage is None
        assert relation.war_alliance is None
