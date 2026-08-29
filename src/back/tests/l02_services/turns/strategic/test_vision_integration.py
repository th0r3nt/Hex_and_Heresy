"""
Туман войны внутри конвейера глобального такта.

Проверяется место шага в пайплайне: обзор обязан считаться после марша,
иначе разведка отставала бы от собственной колонны на целый ход.
"""

import pytest

from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.maps.constants import HexVisibilityState
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.l02_services.turns.strategic.orchestrator import (
    StrategicTurnOrchestrator,
)


def hex_at(q: int) -> HexCoordinates:
    """Гекс на оси экватора - маршруты в этих тестах прямые."""
    return HexCoordinates.from_axial(q, 0)


@pytest.fixture
def world(human_faction) -> WorldState:
    """
    Партия одной державы: цитадель в начале координат, вокруг - Ничья земля.
    """
    world_state = WorldState()
    human_faction.capital_hex = hex_at(0)
    world_state.add_faction(human_faction)
    return world_state


# ==================================================================
# ШАГ ТУМАНА В КОНВЕЙЕРЕ
# ==================================================================


class TestVisionInsideTheTurn:
    async def test_turn_fills_the_vision_report(
        self, world: WorldState, fake_bus
    ):
        orchestrator = StrategicTurnOrchestrator(event_bus=fake_bus)

        report = await orchestrator.execute_turn(world)

        # Цитадель радиусом 2 открывает 19 гексов вокруг себя
        assert report.vision_report.visible_hexes_by_faction["humans"] == 19
        assert report.vision_report.newly_explored_by_faction["humans"] == 19

    async def test_vision_follows_the_march(
        self, world: WorldState, basic_squad, fake_bus
    ):
        """
        Обзор считается по конечной позиции армии: гекс, до которого она
        дошла на этом же такте, уже просматривается.
        """
        army = StrategicArmy(faction_id="humans", name="Разъезд", current_hex=hex_at(0))
        army.add_squad(basic_squad)
        world.add_army(army)

        facade = TurnsFacade(event_bus=fake_bus)
        facade.order_army_march(world, army.id, hex_at(6))
        await facade.execute_strategic_turn(world)

        assert army.current_hex != hex_at(0)
        assert facade.is_hex_visible(world, "humans", army.current_hex)

    async def test_abandoned_hex_falls_back_to_fog(
        self, world: WorldState, basic_squad, fake_bus
    ):
        """
        Гекс, с которого армия ушла за пределы обзора базы, затягивает
        туманом войны - но не черным.
        """
        army = StrategicArmy(faction_id="humans", name="Разъезд", current_hex=hex_at(6))
        army.add_squad(basic_squad)
        world.add_army(army)

        facade = TurnsFacade(event_bus=fake_bus)
        await facade.execute_strategic_turn(world)

        army.current_hex = hex_at(0)
        await facade.execute_strategic_turn(world)

        assert (
            facade.get_hex_visibility(world, "humans", hex_at(6))
            == HexVisibilityState.FOG_OF_WAR
        )

    async def test_explored_history_survives_the_ticks(
        self, world: WorldState, fake_bus
    ):
        """Открытая карта не забывается от такта к такту."""
        facade = TurnsFacade(event_bus=fake_bus)

        await facade.execute_strategic_turn(world)
        await facade.execute_strategic_turn(world)

        vision_map = facade.get_faction_vision(world, "humans")

        assert len(vision_map.explored_hexes) == 19


# ==================================================================
# СРЕЗ МИРА ИЗ ФАСАДА ХОДОВ
# ==================================================================


class TestWorldViewFromFacade:
    async def test_view_hides_the_enemy_beyond_the_horizon(
        self, world: WorldState, orc_faction, fake_bus
    ):
        orc_faction.capital_hex = hex_at(12)
        world.add_faction(orc_faction)
        raiders = StrategicArmy(
            faction_id="greenskins", name="Орда", current_hex=hex_at(9)
        )
        world.add_army(raiders)

        facade = TurnsFacade(event_bus=fake_bus)
        await facade.execute_strategic_turn(world)

        view = facade.get_world_view(world, "humans")

        assert raiders.id not in view.armies

    async def test_view_shows_the_enemy_under_the_walls(
        self, world: WorldState, orc_faction, fake_bus
    ):
        orc_faction.capital_hex = hex_at(12)
        world.add_faction(orc_faction)
        raiders = StrategicArmy(
            faction_id="greenskins", name="Орда", current_hex=hex_at(2)
        )
        world.add_army(raiders)

        facade = TurnsFacade(event_bus=fake_bus)
        await facade.execute_strategic_turn(world)

        view = facade.get_world_view(world, "humans")

        assert raiders.id in view.armies
