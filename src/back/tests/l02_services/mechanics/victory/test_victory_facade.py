"""
Фасад глобальных целей: запись финала в мир, объявление его на шине и
защита от повторного трубления.
"""

import pytest

from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.world.constants import VictoryType
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.victory.facade import VictoryFacade
from src.back.tests.l02_services.mechanics.victory.conftest import (
    FakeEventBus,
    add_towns,
)
from src.back.utils.event.registry import GameEvents

GAME_OVER = GameEvents.GameFlow.GAME_OVER.value


@pytest.fixture
def facade(fake_bus: FakeEventBus) -> VictoryFacade:
    return VictoryFacade(event_bus=fake_bus)


class TestEvaluateWorld:
    @pytest.mark.asyncio
    async def test_idle_party_is_not_announced(
        self, facade: VictoryFacade, fake_bus: FakeEventBus, world: WorldState
    ):
        result = await facade.evaluate_world(world)

        assert not result.is_game_over
        assert world.victory_outcome is None
        assert GAME_OVER not in fake_bus.names()

    @pytest.mark.asyncio
    async def test_victory_is_recorded_and_announced(
        self,
        facade: VictoryFacade,
        fake_bus: FakeEventBus,
        world: WorldState,
        player: Faction,
    ):
        add_towns(player, [4, 4, 4])

        result = await facade.evaluate_world(world)

        assert result.is_game_over
        assert world.victory_outcome is result
        assert world.is_finished

        published = [kwargs for name, kwargs in fake_bus.events if name == GAME_OVER]
        assert len(published) == 1
        assert published[0]["victory_type"] == VictoryType.EXPANSION.value
        assert published[0]["winner_faction_id"] == player.id
        assert published[0]["is_player_victorious"] is True

    @pytest.mark.asyncio
    async def test_party_ends_only_once(
        self,
        facade: VictoryFacade,
        fake_bus: FakeEventBus,
        world: WorldState,
        player: Faction,
    ):
        """
        Следующие такты не должны заново трубить о победе, уже случившейся:
        экран финала показывается один раз.
        """
        add_towns(player, [4, 4, 4])
        first = await facade.evaluate_world(world)

        second = await facade.evaluate_world(world)

        assert second is first
        assert fake_bus.names().count(GAME_OVER) == 1

    @pytest.mark.asyncio
    async def test_recorded_finale_survives_a_reversal(
        self,
        facade: VictoryFacade,
        world: WorldState,
        player: Faction,
    ):
        """Записанный финал не отменяется тем, что мир потом изменился."""
        towns = add_towns(player, [4, 4, 4])
        await facade.evaluate_world(world)

        towns[0].downgrade(2)
        result = await facade.evaluate_world(world)

        assert result.is_game_over
        assert result.victory_type is VictoryType.EXPANSION


class TestReadingProgress:
    def test_progress_is_available_without_ending_the_party(
        self, facade: VictoryFacade, world: WorldState, player: Faction
    ):
        add_towns(player, [4, 3])

        progress = facade.get_faction_progress(world, player.id)

        assert progress.max_level_towns_count == 1
        assert world.victory_outcome is None

    def test_unknown_faction_is_not_considered_defeated(
        self, facade: VictoryFacade, world: WorldState
    ):
        assert not facade.is_faction_defeated(world, "dwarfs")

    def test_razed_faction_is_reported_as_defeated(
        self, facade: VictoryFacade, world: WorldState, rival: Faction
    ):
        rival.headquarters.destroy()

        assert facade.is_faction_defeated(world, rival.id)
