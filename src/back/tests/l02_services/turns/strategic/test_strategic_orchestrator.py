"""
Интеграционные тесты полного цикла конвейера стратегического хода.
"""

import pytest

from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.l02_services.turns.strategic.orchestrator import (
    StrategicTurnOrchestrator,
)
from src.back.utils.event.registry import GameEvents


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
        assert GameEvents.Strategic.TURN_STARTED in event_names
        assert GameEvents.Strategic.TURN_COMPLETED in event_names

    @pytest.mark.asyncio
    async def test_turns_facade_delegation(self, human_faction, sample_army, fake_bus):
        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_army(sample_army)

        facade = TurnsFacade(event_bus=fake_bus)
        report = await facade.execute_strategic_turn(world_state)

        assert report.events_report.ticks_elapsed == 1
        assert human_faction.id in report.economy_reports

    @pytest.mark.asyncio
    async def test_full_turn_includes_service_veterancy_report(
        self, human_faction, sample_army, fake_bus
    ):
        from src.back.l01_domain.army.models.characters.commanders import (
            Commander,
            CommanderArchetype,
            CommanderGenerationType,
            CommanderTrait,
        )

        sample_army.commander = Commander(
            name="Полководец",
            faction_id=human_faction.id,
            generation_type=CommanderGenerationType.PROCEDURAL,
            archetype=CommanderArchetype(id="arch_1", name="A", description="D"),
            trait=CommanderTrait(id="trait_1", name="T", text_fragment="..."),
        )

        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_army(sample_army)

        orchestrator = StrategicTurnOrchestrator(event_bus=fake_bus)
        report = await orchestrator.execute_turn(world_state)

        assert isinstance(report.service_veterancy_candidate_ids, list)
        assert sample_army.squads[0].veterancy.accumulated_service_days > 0.0
