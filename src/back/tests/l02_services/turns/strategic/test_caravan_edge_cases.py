"""
Тесты краевых случаев экспедиций рабочих: уничтожение караванов врагом,
запрет ручного отзыва, невалидные параметры длительности и накопление груза.
"""

import pytest

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions import (
    ExpeditionRecallForbiddenError,
    InvalidAssignmentTargetError,
    WorkerNotAvailableError,
)
from src.back.l01_domain.factions.constants import (
    WorkerAssignmentStatus,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.workers.expedition import (
    ExpeditionWorkerService,
)
from src.back.utils.event.registry import GameEvents


@pytest.fixture
def slave_goblins() -> Squad:
    archetype = UnitArchetype(
        id="unit_goblins_scavengers",
        race=FactionRace.GREENSKINS,
        name="Гоблины-рабы",
        tier=0,
        default_unit_count=100,
        base_stats=BaseUnitStats(max_hp=10.0),
    )
    return Squad.create_new(archetype=archetype)


class TestCaravanExpeditionEdgeCases:
    @pytest.mark.asyncio
    async def test_dispatch_with_zero_or_negative_duration_raises_error(
        self, orc_faction, slave_goblins
    ):
        world = WorldState()
        world.add_faction(orc_faction)
        army = StrategicArmy(
            faction_id=orc_faction.id, current_hex=HexCoordinates.from_axial(0, 0)
        )
        army.add_squad(slave_goblins)
        world.add_army(army)

        service = ExpeditionWorkerService()
        with pytest.raises(InvalidAssignmentTargetError):
            await service.dispatch_expedition(
                world_state=world,
                squad_id=slave_goblins.id,
                faction_id=orc_faction.id,
                target_hex=HexCoordinates.from_axial(2, 0),
                home_hex=HexCoordinates.from_axial(0, 0),
                mining_duration_ticks=0,
            )

    @pytest.mark.asyncio
    async def test_cannot_dispatch_squad_locked_in_tactical_combat(
        self, orc_faction, slave_goblins
    ):
        world = WorldState()
        world.add_faction(orc_faction)
        army = StrategicArmy(
            faction_id=orc_faction.id, current_hex=HexCoordinates.from_axial(0, 0)
        )
        army.add_squad(slave_goblins)
        army.lock_in_tactical_battle()
        world.add_army(army)

        service = ExpeditionWorkerService()
        with pytest.raises(WorkerNotAvailableError) as exc_info:
            await service.dispatch_expedition(
                world_state=world,
                squad_id=slave_goblins.id,
                faction_id=orc_faction.id,
                target_hex=HexCoordinates.from_axial(2, 0),
                home_hex=HexCoordinates.from_axial(0, 0),
                mining_duration_ticks=2,
            )

        assert "связана тактическим боем" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_manual_recall_during_expedition_is_forbidden(
        self, orc_faction, slave_goblins
    ):
        world = WorldState()
        world.add_faction(orc_faction)
        army = StrategicArmy(
            faction_id=orc_faction.id, current_hex=HexCoordinates.from_axial(0, 0)
        )
        army.add_squad(slave_goblins)
        world.add_army(army)

        service = ExpeditionWorkerService()
        assignment = await service.dispatch_expedition(
            world_state=world,
            squad_id=slave_goblins.id,
            faction_id=orc_faction.id,
            target_hex=HexCoordinates.from_axial(2, 0),
            home_hex=HexCoordinates.from_axial(0, 0),
            mining_duration_ticks=2,
        )

        with pytest.raises(ExpeditionRecallForbiddenError):
            assignment.assert_can_unassign_manually()

    @pytest.mark.asyncio
    async def test_caravan_destruction_triggers_expedition_lost_event(
        self, orc_faction, slave_goblins, fake_bus
    ):
        world = WorldState()
        world.add_faction(orc_faction)
        army = StrategicArmy(
            faction_id=orc_faction.id, current_hex=HexCoordinates.from_axial(0, 0)
        )
        army.add_squad(slave_goblins)
        world.add_army(army)

        service = ExpeditionWorkerService(event_bus=fake_bus)
        assignment = await service.dispatch_expedition(
            world_state=world,
            squad_id=slave_goblins.id,
            faction_id=orc_faction.id,
            target_hex=HexCoordinates.from_axial(2, 0),
            home_hex=HexCoordinates.from_axial(0, 0),
            mining_duration_ticks=3,
        )

        caravan_army = world.get_army(assignment.expedition_army_id or "")
        assert caravan_army is not None

        # Враг уничтожает отряд в караване
        caravan_army.squads.clear()

        # Сервис обрабатывает такты и фиксирует гибель
        await service.process_expeditions(world)

        assert assignment.status == WorkerAssignmentStatus.ABORTED
        assert assignment.is_active is False

        event_names = [name for name, _ in fake_bus.events]
        assert GameEvents.Economy.EXPEDITION_LOST in event_names
