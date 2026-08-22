"""
Тесты сервиса учёта выслуги лет (второй, независимый от боевых убийств,
триггер ветеранства - служба в армии полководца).
"""

import pytest

from src.back.l01_domain.army.constants import VETERANCY_SERVICE_DAYS_THRESHOLD
from src.back.l01_domain.army.models.characters.commanders import (
    Commander,
    CommanderArchetype,
    CommanderGenerationType,
    CommanderTrait,
)
from src.back.l01_domain.world.constants import HOURS_PER_DAY
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.veterancy import StrategicVeterancyService


def _make_commander(faction_id: str) -> Commander:
    return Commander(
        name="Тестовый Полководец",
        faction_id=faction_id,
        generation_type=CommanderGenerationType.PROCEDURAL,
        archetype=CommanderArchetype(id="arch_test", name="A", description="D"),
        trait=CommanderTrait(id="trait_test", name="T", text_fragment="..."),
    )


class TestStrategicVeterancyService:
    @pytest.mark.asyncio
    async def test_army_without_commander_does_not_accumulate_service(
        self, human_faction, sample_army
    ):
        """
        sample_army создаётся без полководца (StrategicArmy.commander по
        умолчанию None) - гарнизон/безхозная армия по лору не считается
        "службой в армии полководца".
        """
        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(sample_army)
        assert sample_army.commander is None

        service = StrategicVeterancyService()
        report = await service.process_service_accumulation(world)

        assert report.veterancy_candidate_ids == []
        assert sample_army.squads[0].veterancy.accumulated_service_days == 0.0

    @pytest.mark.asyncio
    async def test_army_with_commander_accumulates_service_days(
        self, human_faction, sample_army
    ):
        sample_army.commander = _make_commander(human_faction.id)

        world = WorldState()
        world.time.hours_per_tick = 4
        world.add_faction(human_faction)
        world.add_army(sample_army)

        service = StrategicVeterancyService()
        report = await service.process_service_accumulation(world)

        expected_days = 4 / HOURS_PER_DAY
        assert report.veterancy_candidate_ids == []
        assert sample_army.squads[0].veterancy.accumulated_service_days == pytest.approx(
            expected_days
        )

    @pytest.mark.asyncio
    async def test_crossing_service_threshold_flags_candidate(
        self, human_faction, sample_army
    ):
        sample_army.commander = _make_commander(human_faction.id)
        squad = sample_army.squads[0]
        squad.veterancy.accumulated_service_days = VETERANCY_SERVICE_DAYS_THRESHOLD - 0.01

        world = WorldState()
        world.time.hours_per_tick = 4
        world.add_faction(human_faction)
        world.add_army(sample_army)

        service = StrategicVeterancyService()
        report = await service.process_service_accumulation(world)

        assert squad.id in report.veterancy_candidate_ids

    @pytest.mark.asyncio
    async def test_accumulation_persists_across_multiple_ticks(
        self, human_faction, sample_army
    ):
        """Многократные вызовы на одной и той же армии суммируются, не сбрасываются."""
        sample_army.commander = _make_commander(human_faction.id)
        squad = sample_army.squads[0]

        world = WorldState()
        world.time.hours_per_tick = 4
        world.add_faction(human_faction)
        world.add_army(sample_army)

        service = StrategicVeterancyService()
        await service.process_service_accumulation(world)
        await service.process_service_accumulation(world)
        await service.process_service_accumulation(world)

        expected_days = 3 * (4 / HOURS_PER_DAY)
        assert squad.veterancy.accumulated_service_days == pytest.approx(expected_days)

    @pytest.mark.asyncio
    async def test_dead_and_named_squads_are_skipped(self, human_faction, sample_army):
        sample_army.commander = _make_commander(human_faction.id)
        squad = sample_army.squads[0]
        squad.veterancy.promote(
            commander_name="Маркус",
            squad_nickname="...",
            trait_name="...",
            lore="...",
        )

        world = WorldState()
        world.add_faction(human_faction)
        world.add_army(sample_army)

        service = StrategicVeterancyService()
        report = await service.process_service_accumulation(world)

        assert report.veterancy_candidate_ids == []
        # уже именной отряд пропущен - накопитель не тронут
        assert squad.veterancy.accumulated_service_days == 0.0
