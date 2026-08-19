"""
Интеграционные тесты полного цикла конвейера стратегического хода.
"""

import pytest

from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.l02_services.turns.strategic.orchestrator import (
    StrategicTurnOrchestrator,
)


class TestStrategicTurnOrchestrator:
    @pytest.mark.asyncio
    async def test_full_strategic_turn_pipeline(self, human_faction, sample_army, fake_bus):
        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_army(sample_army)

        orchestrator = StrategicTurnOrchestrator(event_bus=fake_bus)
        report = await orchestrator.execute_turn(world_state)

        # 1. Проверяем продвижение времени
        assert world_state.time.total_ticks == 1
        assert report.events_report.ticks_elapsed == 1

        # 2. Проверяем отчет экономики
        assert human_faction.id in report.economy_reports
        econ_report = report.economy_reports[human_faction.id]
        assert econ_report.upkeep_gold_required > 0

        # 3. Проверяем отчет перемещений
        assert report.movement_report is not None

        # 4. Проверяем события в шине
        event_names = [name for name, _ in fake_bus.events]
        assert "strategic.turn_started" in event_names
        assert "strategic.turn_completed" in event_names

    @pytest.mark.asyncio
    async def test_turns_facade_delegation(self, human_faction, sample_army, fake_bus):
        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_army(sample_army)

        facade = TurnsFacade(event_bus=fake_bus)
        report = await facade.execute_strategic_turn(world_state)

        assert report.events_report.ticks_elapsed == 1
        assert human_faction.id in report.economy_reports
