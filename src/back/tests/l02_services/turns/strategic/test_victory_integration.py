"""
Глобальные цели в конвейере хода и в игровом потоке.

Здесь проверяется не арифметика порогов (она в тестах оценщика), а стыки:
доезжает ли вердикт такта до конечного автомата и запускает ли штурм
цитадели внеочередную проверку.
"""

import pytest

from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.border_town import BorderTown
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.constants import (
    VICTORY_ECONOMIC_FOOD,
    VICTORY_ECONOMIC_GOLD,
    VICTORY_ECONOMIC_MATERIAL,
    VictoryType,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.gameflow.facade import GameFlowFacade
from src.back.l02_services.gameflow.fsm import GameFlowFSM
from src.back.l02_services.gameflow.states import GameState
from src.back.l02_services.mechanics.victory.facade import VictoryFacade
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.l02_services.turns.strategic.orchestrator import (
    StrategicTurnOrchestrator,
)
from src.back.utils.event.registry import GameEvents

CAPITAL_HEX = HexCoordinates.from_axial(0, 0)


def build_gameflow(
    world_state: WorldState,
    victory_facade: VictoryFacade,
    state: GameState = GameState.STRATEGIC_MAP,
) -> GameFlowFacade:
    """Игровой поток идущей партии с подключенной подсистемой целей."""
    gameflow = GameFlowFacade(
        fsm=GameFlowFSM(initial_state=state), victory_facade=victory_facade
    )
    gameflow.bind_world_state(world_state)
    return gameflow


def make_rich(faction: Faction) -> None:
    """Доводит казну ровно до всех трех порогов процветания."""
    faction.resources[ResourceType.GOLD] = VICTORY_ECONOMIC_GOLD
    faction.resources[ResourceType.MATERIAL] = VICTORY_ECONOMIC_MATERIAL
    faction.resources[ResourceType.FOOD] = VICTORY_ECONOMIC_FOOD


# ==================================================================
# ШАГ 4.8 В КОНВЕЙЕРЕ ТАКТА
# ==================================================================


class TestVictoryInStrategicTurn:
    @pytest.mark.asyncio
    async def test_turn_report_carries_victory_progress(
        self, human_faction, orc_faction, fake_bus
    ):
        """Каждый такт кладет в отчет срез прогресса всех сторон."""
        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_faction(orc_faction)

        report = await StrategicTurnOrchestrator(event_bus=fake_bus).execute_turn(
            world_state
        )

        assert not report.victory_result.is_game_over
        assert set(report.victory_result.progress) == {human_faction.id, orc_faction.id}

    @pytest.mark.asyncio
    async def test_reached_thresholds_move_the_fsm_to_game_over(
        self, human_faction, orc_faction, fake_bus
    ):
        """
        Фракция игрока добирает пороги ресурсов - и такт сам переводит игру
        на экран финала, не дожидаясь команды снаружи.
        """
        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_faction(orc_faction)
        make_rich(human_faction)

        victory_facade = VictoryFacade(event_bus=fake_bus)
        gameflow = build_gameflow(world_state, victory_facade)

        report = await StrategicTurnOrchestrator(
            victory_facade=victory_facade,
            gameflow_facade=gameflow,
            event_bus=fake_bus,
        ).execute_turn(world_state)

        assert report.victory_result.is_game_over
        assert report.victory_result.victory_type is VictoryType.ECONOMIC
        assert gameflow.current_state == GameState.GAME_OVER
        assert GameEvents.GameFlow.GAME_OVER in [name for name, _ in fake_bus.events]

    @pytest.mark.asyncio
    async def test_turn_without_gameflow_only_reports_the_verdict(
        self, human_faction, orc_faction, fake_bus
    ):
        """
        Без игрового потока такт все равно считает цели: вердикт уезжает в
        отчет, а переключать экраны некому.
        """
        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_faction(orc_faction)
        make_rich(human_faction)

        report = await StrategicTurnOrchestrator(event_bus=fake_bus).execute_turn(
            world_state
        )

        assert report.victory_result.is_game_over
        assert world_state.is_finished

    @pytest.mark.asyncio
    async def test_next_turn_does_not_declare_the_finale_twice(
        self, human_faction, orc_faction, fake_bus
    ):
        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_faction(orc_faction)
        make_rich(human_faction)

        orchestrator = StrategicTurnOrchestrator(event_bus=fake_bus)
        await orchestrator.execute_turn(world_state)
        await orchestrator.execute_turn(world_state)

        announcements = [
            name for name, _ in fake_bus.events if name == GameEvents.GameFlow.GAME_OVER
        ]
        assert len(announcements) == 1


# ==================================================================
# ЧТЕНИЕ ПРОГРЕССА ЧЕРЕЗ ФАСАД ХОДОВ
# ==================================================================


class TestTurnsFacadeVictoryReading:
    def test_progress_is_readable_without_running_a_turn(
        self, human_faction, fake_bus
    ):
        world_state = WorldState()
        world_state.add_faction(human_faction)
        human_faction.add_border_town(
            BorderTown(
                faction_id=human_faction.id,
                name="Застава",
                level=4,
                center_hex=HexCoordinates.from_axial(5, -5),
            )
        )

        progress = TurnsFacade(event_bus=fake_bus).get_victory_progress(
            world_state, human_faction.id
        )

        assert progress.max_level_towns_count == 1
        assert world_state.time.total_ticks == 0


# ==================================================================
# ВНЕОЧЕРЕДНАЯ ПРОВЕРКА ПОСЛЕ ШТУРМА
# ==================================================================


class TestVictoryAfterTacticalCombat:
    @pytest.mark.asyncio
    async def test_razed_capital_ends_the_party_right_after_the_battle(
        self, human_faction, orc_faction, fake_bus
    ):
        """
        Последняя вражеская цитадель падает - и партия заканчивается тем же
        запросом, а не следующим тактом.
        """
        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_faction(orc_faction)
        orc_faction.capital_hex = CAPITAL_HEX

        victory_facade = VictoryFacade(event_bus=fake_bus)
        gameflow = build_gameflow(world_state, victory_facade)

        battle = TacticalBattleState()
        await gameflow.enter_tactical_combat(
            hex_coords=CAPITAL_HEX,
            attacker_faction_id=human_faction.id,
            defender_faction_id=orc_faction.id,
            battle_state=battle,
        )

        state = await gameflow.finish_tactical_combat(
            battle_id=battle.id,
            victor_faction_id=human_faction.id,
            is_base_destroyed=True,
        )

        assert orc_faction.headquarters.is_destroyed
        assert state == GameState.GAME_OVER
        assert world_state.victory_outcome.victory_type is VictoryType.DOMINATION

    @pytest.mark.asyncio
    async def test_players_own_razed_capital_ends_the_party_as_a_loss(
        self, human_faction, orc_faction, fake_bus
    ):
        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_faction(orc_faction)
        human_faction.capital_hex = CAPITAL_HEX

        victory_facade = VictoryFacade(event_bus=fake_bus)
        gameflow = build_gameflow(world_state, victory_facade)

        battle = TacticalBattleState()
        await gameflow.enter_tactical_combat(
            hex_coords=CAPITAL_HEX,
            attacker_faction_id=orc_faction.id,
            defender_faction_id=human_faction.id,
            battle_state=battle,
        )
        await gameflow.finish_tactical_combat(
            battle_id=battle.id,
            victor_faction_id=orc_faction.id,
            is_base_destroyed=True,
        )

        assert gameflow.current_state == GameState.GAME_OVER
        assert not world_state.victory_outcome.is_player_victorious

    @pytest.mark.asyncio
    async def test_razed_border_town_does_not_touch_the_citadel(
        self, human_faction, orc_faction, fake_bus
    ):
        """
        Снесенный пограничный город - потеря поселения, а не конец фракции:
        цитадель стоит на другом гексе и остается цела.
        """
        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_faction(orc_faction)
        orc_faction.capital_hex = CAPITAL_HEX

        town_hex = HexCoordinates.from_axial(6, -6)
        victory_facade = VictoryFacade(event_bus=fake_bus)
        gameflow = build_gameflow(world_state, victory_facade)

        battle = TacticalBattleState()
        await gameflow.enter_tactical_combat(
            hex_coords=town_hex,
            attacker_faction_id=human_faction.id,
            defender_faction_id=orc_faction.id,
            battle_state=battle,
        )
        state = await gameflow.finish_tactical_combat(
            battle_id=battle.id,
            victor_faction_id=human_faction.id,
            is_base_destroyed=True,
        )

        assert not orc_faction.headquarters.is_destroyed
        assert state == GameState.STRATEGIC_MAP

    @pytest.mark.asyncio
    async def test_ordinary_battle_does_not_check_the_goals(
        self, human_faction, orc_faction, fake_bus
    ):
        """Без разрушенной базы бой заканчивается как обычно, возвратом на карту."""
        world_state = WorldState()
        world_state.add_faction(human_faction)
        world_state.add_faction(orc_faction)
        orc_faction.capital_hex = CAPITAL_HEX

        victory_facade = VictoryFacade(event_bus=fake_bus)
        gameflow = build_gameflow(world_state, victory_facade)

        battle = TacticalBattleState()
        await gameflow.enter_tactical_combat(
            hex_coords=CAPITAL_HEX,
            attacker_faction_id=human_faction.id,
            defender_faction_id=orc_faction.id,
            battle_state=battle,
        )
        state = await gameflow.finish_tactical_combat(
            battle_id=battle.id, victor_faction_id=human_faction.id
        )

        assert state == GameState.STRATEGIC_MAP
        assert world_state.victory_outcome is None
