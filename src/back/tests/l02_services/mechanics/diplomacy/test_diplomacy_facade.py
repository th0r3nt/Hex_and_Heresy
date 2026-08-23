"""
Тесты фасада дипломатии: сборка дипломатического отчета такта,
выплата дани и работа шага дипломатии внутри глобального такта.
"""

import pytest

from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.diplomacy.pacts import TradeAgreement
from src.back.l02_services.mechanics.diplomacy.facade import DiplomacyFacade
from src.back.l02_services.turns.strategic.orchestrator import StrategicTurnOrchestrator
from src.back.utils.event.registry import GameEvents


class TestDiplomacyTick:
    @pytest.mark.asyncio
    async def test_tick_report_collects_logistics_and_pacts(self, world, fake_bus):
        facade = DiplomacyFacade(event_bus=fake_bus)
        relation = world.get_or_create_relation("humans", "elfs")
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
        dispatch = await facade.send_dispatch(world, "humans", "elfs", "Мир?")
        ambassador = await facade.send_ambassador(world, "humans", "Граф Вальтер", "elfs")

        first_report = await facade.process_tick(world)

        assert first_report.expired_pacts == ["humans:elfs:trade_agreement"]
        assert first_report.delivered_dispatch_ids == []
        assert first_report.arrived_ambassador_ids == []

        # Гонец доезжает за два такта, посол идет пешком четыре
        second_report = await facade.process_tick(world)
        assert second_report.delivered_dispatch_ids == [dispatch.id]

        await facade.process_tick(world)
        fourth_report = await facade.process_tick(world)
        assert fourth_report.arrived_ambassador_ids == [ambassador.id]

    @pytest.mark.asyncio
    async def test_pay_tribute_moves_gold_and_closes_demand(self, world, humans, elfs, fake_bus):
        facade = DiplomacyFacade(event_bus=fake_bus)
        relation = world.get_or_create_relation("humans", "elfs")
        relation.demand_tribute(250.0)

        paid = await facade.pay_tribute(world, "humans", "elfs")

        assert paid == 250.0
        assert humans.resources[ResourceType.GOLD] == 750.0
        assert elfs.resources[ResourceType.GOLD] == 1250.0
        assert relation.tribute_demanded_gold is None
        assert GameEvents.Diplomacy.TRIBUTE_PAID in fake_bus.names()

    @pytest.mark.asyncio
    async def test_pay_tribute_without_demand_does_nothing(self, world, humans):
        facade = DiplomacyFacade()

        assert await facade.pay_tribute(world, "humans", "elfs") == 0.0
        assert humans.resources[ResourceType.GOLD] == 1000.0


class TestDiplomacyInsideStrategicTurn:
    @pytest.mark.asyncio
    async def test_dispatch_travels_across_global_ticks(self, world, fake_bus):
        facade = DiplomacyFacade(event_bus=fake_bus)
        orchestrator = StrategicTurnOrchestrator(
            diplomacy_facade=facade, event_bus=fake_bus
        )
        dispatch = await facade.send_dispatch(world, "humans", "elfs", "Предлагаю союз.")

        first_turn = await orchestrator.execute_turn(world)
        assert first_turn.diplomacy_report.delivered_dispatch_ids == []
        assert world.dispatches == [dispatch]

        second_turn = await orchestrator.execute_turn(world)
        assert second_turn.diplomacy_report.delivered_dispatch_ids == [dispatch.id]
        assert world.dispatches == []
