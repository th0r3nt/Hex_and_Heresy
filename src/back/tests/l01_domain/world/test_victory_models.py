"""
Модели глобальных целей партии: пороги, их инварианты и арифметика полосок
прогресса.

Здесь проверяется только доменная математика - собирает ли замер по миру
VictoryEvaluator, эти тесты не знают.
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.factions.constants import MAX_BORDER_TOWN_LEVEL
from src.back.l01_domain.world.constants import (
    VICTORY_ECONOMIC_FOOD,
    VICTORY_ECONOMIC_GOLD,
    VICTORY_ECONOMIC_MATERIAL,
    VICTORY_EXPANSION_TOWNS_COUNT,
    VICTORY_EXPANSION_TOWN_LEVEL,
    VictoryType,
)
from src.back.l01_domain.world.models.victory import (
    VictoryConditionConfig,
    VictoryEvaluationResult,
    VictoryProgress,
)


def _progress(**overrides) -> VictoryProgress:
    """Замер игрока, у которого еще ничего не выполнено."""
    defaults = dict(faction_id="humans")
    defaults.update(overrides)
    return VictoryProgress(**defaults)


# ==================================================================
# НАСТРОЙКИ ПАРТИИ
# ==================================================================


class TestVictoryConditionConfig:
    def test_defaults_repeat_the_rulebook(self):
        config = VictoryConditionConfig()

        assert config.gold_threshold == VICTORY_ECONOMIC_GOLD
        assert config.material_threshold == VICTORY_ECONOMIC_MATERIAL
        assert config.food_threshold == VICTORY_ECONOMIC_FOOD
        assert config.towns_count == VICTORY_EXPANSION_TOWNS_COUNT
        assert config.town_level == VICTORY_EXPANSION_TOWN_LEVEL

    def test_all_three_branches_are_played_by_default(self):
        assert VictoryConditionConfig().enabled_types == (
            VictoryType.DOMINATION,
            VictoryType.ECONOMIC,
            VictoryType.EXPANSION,
        )

    def test_disabled_branch_drops_out_of_the_order(self):
        config = VictoryConditionConfig(is_economic_enabled=False)

        assert config.enabled_types == (VictoryType.DOMINATION, VictoryType.EXPANSION)
        assert not config.is_enabled(VictoryType.ECONOMIC)

    def test_town_level_cannot_exceed_the_ceiling_of_a_town(self):
        """Города выше четвертого уровня не бывает - такой цели тоже."""
        with pytest.raises(ValidationError):
            VictoryConditionConfig(town_level=MAX_BORDER_TOWN_LEVEL + 1)

    def test_negative_threshold_is_rejected(self):
        with pytest.raises(ValidationError):
            VictoryConditionConfig(gold_threshold=-1.0)

    def test_config_is_frozen(self):
        """Правила партии не двигаются посреди игры."""
        config = VictoryConditionConfig()
        with pytest.raises(ValidationError):
            config.gold_threshold = 1.0


# ==================================================================
# ЗАМЕР ПРОГРЕССА
# ==================================================================


class TestDominationProgress:
    def test_all_enemies_defeated_completes_the_branch(self):
        progress = _progress(
            domination_defeated_factions=2, domination_total_enemies=2
        )

        assert progress.is_domination_complete
        assert progress.domination_ratio == pytest.approx(1.0)

    def test_last_standing_enemy_blocks_the_branch(self):
        progress = _progress(
            domination_defeated_factions=1, domination_total_enemies=2
        )

        assert not progress.is_domination_complete
        assert progress.domination_ratio == pytest.approx(0.5)

    def test_solitude_is_not_a_victory(self):
        """Партия без соперников не выигрывается господством: побеждать некого."""
        progress = _progress(
            domination_defeated_factions=0, domination_total_enemies=0
        )

        assert not progress.is_domination_complete

    def test_more_defeated_than_existing_is_invalid(self):
        with pytest.raises(ValidationError):
            _progress(domination_defeated_factions=3, domination_total_enemies=2)


class TestEconomicProgress:
    def test_all_three_thresholds_taken_at_once(self):
        progress = _progress(
            current_gold=VICTORY_ECONOMIC_GOLD,
            current_material=VICTORY_ECONOMIC_MATERIAL,
            current_food=VICTORY_ECONOMIC_FOOD,
        )

        assert progress.is_economic_complete
        assert progress.economic_ratio == pytest.approx(1.0)

    @pytest.mark.parametrize(
        "lacking_field",
        ["current_gold", "current_material", "current_food"],
    )
    def test_one_unit_short_blocks_the_victory(self, lacking_field: str):
        """Нехватка единицы любого ресурса рушит экономическую победу целиком."""
        values = {
            "current_gold": VICTORY_ECONOMIC_GOLD,
            "current_material": VICTORY_ECONOMIC_MATERIAL,
            "current_food": VICTORY_ECONOMIC_FOOD,
        }
        values[lacking_field] -= 1.0

        assert not _progress(**values).is_economic_complete

    def test_ratio_follows_the_emptiest_storehouse(self):
        """Гора золота не закрывает пустых амбаров: полоска идет по худшему."""
        progress = _progress(
            current_gold=VICTORY_ECONOMIC_GOLD,
            current_material=VICTORY_ECONOMIC_MATERIAL,
            current_food=VICTORY_ECONOMIC_FOOD / 4,
        )

        assert progress.economic_ratio == pytest.approx(0.25)


class TestExpansionProgress:
    def test_three_developed_towns_complete_the_branch(self):
        progress = _progress(max_level_towns_count=VICTORY_EXPANSION_TOWNS_COUNT)

        assert progress.is_expansion_complete
        assert progress.expansion_ratio == pytest.approx(1.0)

    def test_two_developed_towns_are_not_enough(self):
        progress = _progress(max_level_towns_count=2)

        assert not progress.is_expansion_complete
        assert progress.expansion_ratio == pytest.approx(2 / 3)


class TestProgressLookups:
    def test_is_complete_dispatches_to_the_right_branch(self):
        progress = _progress(max_level_towns_count=VICTORY_EXPANSION_TOWNS_COUNT)

        assert progress.is_complete(VictoryType.EXPANSION)
        assert not progress.is_complete(VictoryType.ECONOMIC)
        assert not progress.is_complete(VictoryType.DOMINATION)

    def test_ratio_is_clamped_to_one(self):
        """Перебор ресурсов не растягивает полоску за сто процентов."""
        progress = _progress(
            current_gold=VICTORY_ECONOMIC_GOLD * 10,
            current_material=VICTORY_ECONOMIC_MATERIAL * 10,
            current_food=VICTORY_ECONOMIC_FOOD * 10,
        )

        assert progress.ratio(VictoryType.ECONOMIC) == pytest.approx(1.0)


# ==================================================================
# ВЕРДИКТ
# ==================================================================


class TestVictoryEvaluationResult:
    def test_idle_verdict_ends_nothing(self):
        result = VictoryEvaluationResult()

        assert not result.is_game_over
        assert result.victory_type is None
        assert result.winner_faction_id is None

    def test_progress_is_looked_up_by_faction(self):
        progress = _progress()
        result = VictoryEvaluationResult(progress={progress.faction_id: progress})

        assert result.get_progress("humans") is progress
        assert result.get_progress("greenskins") is None
