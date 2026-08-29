"""
Проверка условий победы и поражения по состоянию мира.

Каждая ветка проверяется на границе: победа обязана присуждаться ровно в
тот момент, когда порог взят, и не раньше.
"""

import pytest

from src.back.l01_domain.exceptions.factions import FactionNotFoundError
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.world.constants import (
    VICTORY_ECONOMIC_FOOD,
    VICTORY_ECONOMIC_GOLD,
    VICTORY_ECONOMIC_MATERIAL,
    VictoryType,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l01_domain.world.models.victory import VictoryConditionConfig
from src.back.l02_services.mechanics.victory.evaluator import VictoryEvaluator
from src.back.tests.l02_services.mechanics.victory.conftest import (
    add_towns,
    build_faction,
    ruin_faction,
)


@pytest.fixture
def evaluator() -> VictoryEvaluator:
    return VictoryEvaluator()


def enrich(faction: Faction, gold: float, material: float, food: float) -> None:
    """Кладет фракции ровно столько ресурсов, сколько сказано."""
    faction.resources[ResourceType.GOLD] = gold
    faction.resources[ResourceType.MATERIAL] = material
    faction.resources[ResourceType.FOOD] = food


# ==================================================================
# ВЫБЫВАНИЕ ФРАКЦИИ
# ==================================================================


class TestFactionDefeat:
    def test_living_faction_is_not_defeated(
        self, evaluator: VictoryEvaluator, world: WorldState, player: Faction
    ):
        assert not evaluator.is_faction_defeated(world, player)

    def test_razed_headquarters_ends_the_faction(
        self, evaluator: VictoryEvaluator, world: WorldState, player: Faction
    ):
        player.headquarters.destroy()

        assert evaluator.is_faction_defeated(world, player)

    def test_total_ruin_ends_the_faction(
        self, evaluator: VictoryEvaluator, world: WorldState, player: Faction
    ):
        """Ни войск, ни земель, ни построек, ни казны - подниматься не с чего."""
        ruin_faction(player)

        assert evaluator.is_faction_defeated(world, player)

    def test_empty_treasury_alone_is_only_a_hard_tick(
        self, evaluator: VictoryEvaluator, world: WorldState, player: Faction
    ):
        """Пустая казна при живом городе - тяжелый такт, а не конец партии."""
        ruin_faction(player)
        add_towns(player, [1])

        assert not evaluator.is_faction_defeated(world, player)


# ==================================================================
# ПОРАЖЕНИЕ ИГРОКА
# ==================================================================


class TestPlayerDefeat:
    def test_player_defeat_when_capital_falls(
        self, evaluator: VictoryEvaluator, world: WorldState, player: Faction
    ):
        player.headquarters.destroy()

        result = evaluator.evaluate(world)

        assert result.is_game_over
        assert not result.is_player_victorious
        assert result.victory_type is None
        assert result.winner_faction_id is None
        assert "пала под штурмом" in result.reason

    def test_defeat_outranks_own_unfinished_goals(
        self, evaluator: VictoryEvaluator, world: WorldState, player: Faction
    ):
        """
        Игрок с полной казной, но без цитадели, проигрывает: экономическую
        победу мертвой державе не присуждают.
        """
        enrich(
            player,
            VICTORY_ECONOMIC_GOLD,
            VICTORY_ECONOMIC_MATERIAL,
            VICTORY_ECONOMIC_FOOD,
        )
        player.headquarters.destroy()

        result = evaluator.evaluate(world)

        assert result.is_game_over
        assert not result.is_player_victorious

    def test_world_without_player_never_ends(
        self, evaluator: VictoryEvaluator, rival: Faction
    ):
        """Партия-наблюдение не заканчивается: некому ни выиграть, ни проиграть."""
        world_state = WorldState()
        world_state.add_faction(rival)
        enrich(
            rival,
            VICTORY_ECONOMIC_GOLD,
            VICTORY_ECONOMIC_MATERIAL,
            VICTORY_ECONOMIC_FOOD,
        )

        result = evaluator.evaluate(world_state)

        assert not result.is_game_over
        assert rival.id in result.progress


# ==================================================================
# ТЕРРИТОРИАЛЬНОЕ ГОСПОДСТВО
# ==================================================================


class TestDominationVictory:
    def test_domination_victory_when_all_enemy_capitals_destroyed(
        self,
        evaluator: VictoryEvaluator,
        world: WorldState,
        player: Faction,
        rival: Faction,
    ):
        rival.headquarters.destroy()

        result = evaluator.evaluate(world)

        assert result.is_game_over
        assert result.is_player_victorious
        assert result.victory_type is VictoryType.DOMINATION
        assert result.winner_faction_id == player.id

    def test_last_standing_enemy_keeps_the_party_going(
        self, evaluator: VictoryEvaluator, world: WorldState, player: Faction
    ):
        """Победа присуждается ровно в момент падения последней базы, не раньше."""
        second_rival = build_faction("elfs", "Дом Серебряной Ветви")
        world.add_faction(second_rival)
        world.get_faction("greenskins").headquarters.destroy()

        assert not evaluator.evaluate(world).is_game_over

        second_rival.headquarters.destroy()
        result = evaluator.evaluate(world)

        assert result.is_game_over
        assert result.victory_type is VictoryType.DOMINATION

    def test_lonely_player_does_not_win_by_domination(
        self, evaluator: VictoryEvaluator, solo_world: WorldState
    ):
        assert not evaluator.evaluate(solo_world).is_game_over


# ==================================================================
# ЭКОНОМИЧЕСКОЕ ПРОЦВЕТАНИЕ
# ==================================================================


class TestEconomicVictory:
    def test_economic_victory_on_exact_thresholds(
        self,
        evaluator: VictoryEvaluator,
        world: WorldState,
        player: Faction,
    ):
        enrich(
            player,
            VICTORY_ECONOMIC_GOLD,
            VICTORY_ECONOMIC_MATERIAL,
            VICTORY_ECONOMIC_FOOD,
        )

        result = evaluator.evaluate(world)

        assert result.is_game_over
        assert result.is_player_victorious
        assert result.victory_type is VictoryType.ECONOMIC

    def test_one_unit_short_blocks_the_victory(
        self,
        evaluator: VictoryEvaluator,
        world: WorldState,
        player: Faction,
    ):
        enrich(
            player,
            VICTORY_ECONOMIC_GOLD,
            VICTORY_ECONOMIC_MATERIAL,
            VICTORY_ECONOMIC_FOOD - 1.0,
        )

        assert not evaluator.evaluate(world).is_game_over

    def test_disabled_branch_is_not_checked(
        self,
        evaluator: VictoryEvaluator,
        world: WorldState,
        player: Faction,
    ):
        """Выключенная в лобби ветка не срабатывает даже на полной казне."""
        world.victory_config = VictoryConditionConfig(is_economic_enabled=False)
        enrich(
            player,
            VICTORY_ECONOMIC_GOLD,
            VICTORY_ECONOMIC_MATERIAL,
            VICTORY_ECONOMIC_FOOD,
        )

        assert not evaluator.evaluate(world).is_game_over

    def test_scenario_thresholds_override_the_defaults(
        self,
        evaluator: VictoryEvaluator,
        world: WorldState,
        player: Faction,
    ):
        world.victory_config = VictoryConditionConfig(
            gold_threshold=10.0, material_threshold=10.0, food_threshold=10.0
        )
        enrich(player, 10.0, 10.0, 10.0)

        result = evaluator.evaluate(world)

        assert result.is_game_over
        assert result.victory_type is VictoryType.ECONOMIC


# ==================================================================
# ОСНОВАНИЕ СТРАНЫ
# ==================================================================


class TestExpansionVictory:
    def test_three_tier_4_towns_win_the_party(
        self,
        evaluator: VictoryEvaluator,
        world: WorldState,
        player: Faction,
    ):
        add_towns(player, [4, 4, 4])

        result = evaluator.evaluate(world)

        assert result.is_game_over
        assert result.is_player_victorious
        assert result.victory_type is VictoryType.EXPANSION

    def test_two_developed_and_two_lagging_towns_are_not_enough(
        self,
        evaluator: VictoryEvaluator,
        world: WorldState,
        player: Faction,
    ):
        """Четыре города не заменяют трех развитых: в зачет идет только уровень."""
        add_towns(player, [4, 4, 3, 3])

        assert not evaluator.evaluate(world).is_game_over

    def test_pillaged_town_rolls_the_progress_back(
        self,
        evaluator: VictoryEvaluator,
        world: WorldState,
        player: Faction,
    ):
        """
        Разграбление сбивает город до второго уровня - и партия, только что
        выигранная, продолжается.
        """
        towns = add_towns(player, [4, 4, 4])
        assert evaluator.evaluate(world).is_game_over

        towns[0].downgrade(2)

        result = evaluator.evaluate(world)
        assert not result.is_game_over
        assert result.progress[player.id].max_level_towns_count == 2


# ==================================================================
# ПОБЕДА СОПЕРНИКА
# ==================================================================


class TestRivalVictory:
    def test_rival_goal_ends_the_party_as_a_loss(
        self,
        evaluator: VictoryEvaluator,
        world: WorldState,
        rival: Faction,
    ):
        add_towns(rival, [4, 4, 4])

        result = evaluator.evaluate(world)

        assert result.is_game_over
        assert not result.is_player_victorious
        assert result.victory_type is VictoryType.EXPANSION
        assert result.winner_faction_id == rival.id
        assert rival.name in result.reason

    def test_defeated_rival_wins_nothing(
        self,
        evaluator: VictoryEvaluator,
        world: WorldState,
        rival: Faction,
    ):
        """Выбывшей фракции цель не засчитывается, даже если склады полны."""
        enrich(
            rival,
            VICTORY_ECONOMIC_GOLD,
            VICTORY_ECONOMIC_MATERIAL,
            VICTORY_ECONOMIC_FOOD,
        )
        rival.headquarters.destroy()

        result = evaluator.evaluate(world)

        # Партия все равно кончилась - но господством игрока, а не победой соперника
        assert result.is_player_victorious
        assert result.victory_type is VictoryType.DOMINATION


# ==================================================================
# ЗАМЕР ПРОГРЕССА
# ==================================================================


class TestProgressCalculation:
    def test_progress_is_taken_for_every_side(
        self, evaluator: VictoryEvaluator, world: WorldState
    ):
        result = evaluator.evaluate(world)

        assert set(result.progress) == {"humans", "greenskins"}

    def test_progress_reads_the_treasury_and_the_towns(
        self,
        evaluator: VictoryEvaluator,
        world: WorldState,
        player: Faction,
    ):
        enrich(player, 1500.0, 200.0, 40.0)
        add_towns(player, [4, 2])

        progress = evaluator.calculate_progress(world, player.id)

        assert progress.current_gold == pytest.approx(1500.0)
        assert progress.max_level_towns_count == 1
        assert progress.domination_total_enemies == 1
        assert progress.domination_defeated_factions == 0

    def test_progress_of_unknown_faction_is_an_error(
        self, evaluator: VictoryEvaluator, world: WorldState
    ):
        with pytest.raises(FactionNotFoundError):
            evaluator.calculate_progress(world, "dwarfs")
