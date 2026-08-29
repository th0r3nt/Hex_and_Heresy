"""
Настройки новой партии: валидация состава сторон и таблицы стартовых
ресурсов по уровням сложности.

Модели лобби ничего не собирают - они лишь не пропускают дальше набор
настроек, по которому мир заведомо не построить.
"""

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions.world import InvalidStartingSetupError
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.world.constants import (
    DifficultyLevel,
    starting_resources,
)
from src.back.l01_domain.world.models.setup import (
    FactionSetupConfig,
    NewGameConfig,
    RulerSetupConfig,
)


# ==================================================================
# ВСПОМОГАТЕЛЬНОЕ
# ==================================================================


def _player_side(**overrides) -> FactionSetupConfig:
    defaults = {
        "race": FactionRace.HUMANS,
        "name": "Империя",
        "is_player_controlled": True,
    }
    return FactionSetupConfig(**{**defaults, **overrides})


def _rival_side(**overrides) -> FactionSetupConfig:
    defaults = {
        "race": FactionRace.GREENSKINS,
        "name": "Орда",
        "is_player_controlled": False,
    }
    return FactionSetupConfig(**{**defaults, **overrides})


# ==================================================================
# ПРАВИТЕЛЬ СТОРОНЫ
# ==================================================================


def test_empty_ruler_leaves_choice_to_generator():
    """Игрок не выбирал правителя - решение остается за генератором."""
    assert RulerSetupConfig().is_empty is True


def test_ruler_accepts_single_source():
    ruler = RulerSetupConfig(legendary_lord_id="lord_hum_benedict_strauss")

    assert ruler.is_empty is False
    assert ruler.custom_lord is None


def test_ruler_rejects_two_sources_at_once():
    """Трон один: и легенду, и своего лорда посадить на него нельзя."""
    with pytest.raises(InvalidStartingSetupError):
        RulerSetupConfig(
            legendary_lord_id="lord_hum_benedict_strauss",
            custom_lord=Lord(faction_id="f1", name="Самозванец"),
        )


# ==================================================================
# ОТДЕЛЬНАЯ СТОРОНА
# ==================================================================


@pytest.mark.parametrize(
    "race",
    [
        FactionRace.HUMANS,
        FactionRace.GREENSKINS,
        FactionRace.ELFS,
        FactionRace.BARONIAL_TROOPS,
        FactionRace.CONGREGATION_OF_THE_METEORITE,
    ],
)
def test_playable_races_are_accepted(race: FactionRace):
    assert FactionSetupConfig(race=race, name="Держава").race == race


@pytest.mark.parametrize("race", [FactionRace.MERCENARIES, FactionRace.NEUTRALS])
def test_non_playable_races_are_rejected(race: FactionRace):
    """У наемников и нейтралов нет ни цитадели, ни правителя."""
    with pytest.raises(InvalidStartingSetupError):
        FactionSetupConfig(race=race, name="Держава")


# ==================================================================
# ПАРТИЯ ЦЕЛИКОМ
# ==================================================================


def test_config_requires_exactly_one_player():
    with pytest.raises(InvalidStartingSetupError):
        NewGameConfig(
            player_faction=_player_side(is_player_controlled=False),
            rival_faction=_rival_side(),
        )

    with pytest.raises(InvalidStartingSetupError):
        NewGameConfig(
            player_faction=_player_side(),
            rival_faction=_rival_side(is_player_controlled=True),
        )


def test_seed_is_generated_when_player_did_not_pick_one():
    """Партия без явного сида все равно воспроизводима: зерно ей выдается."""
    config = NewGameConfig(player_faction=_player_side(), rival_faction=_rival_side())

    assert config.seed is not None


def test_mirror_match_is_allowed():
    """Раса против самой себя - законная партия, а не ошибка настроек."""
    config = NewGameConfig(
        player_faction=_player_side(),
        rival_faction=_rival_side(race=FactionRace.HUMANS, name="Мятежные провинции"),
    )

    assert config.rival_faction.race == config.player_faction.race


def test_baronies_join_the_party_as_third_side():
    config = NewGameConfig(
        player_faction=_player_side(), rival_faction=_rival_side(), include_baronies=True
    )

    sides = config.starting_sides

    assert len(sides) == 3
    assert sides[2].race == FactionRace.BARONIAL_TROOPS
    assert sides[2].is_player_controlled is False


def test_baronies_can_be_switched_off():
    config = NewGameConfig(
        player_faction=_player_side(),
        rival_faction=_rival_side(),
        include_baronies=False,
    )

    assert len(config.starting_sides) == 2


# ==================================================================
# СТАРТОВЫЕ РЕСУРСЫ ПО СЛОЖНОСТЯМ
# ==================================================================


@pytest.mark.parametrize(
    "difficulty, expected_gold",
    [
        (DifficultyLevel.EASY, 1500.0),
        (DifficultyLevel.NORMAL, 1000.0),
        (DifficultyLevel.HARD, 600.0),
    ],
)
def test_player_treasury_shrinks_with_difficulty(
    difficulty: DifficultyLevel, expected_gold: float
):
    assert starting_resources(difficulty, True)[ResourceType.GOLD] == expected_gold


@pytest.mark.parametrize(
    "difficulty, expected_gold",
    [
        (DifficultyLevel.EASY, 800.0),
        (DifficultyLevel.NORMAL, 1000.0),
        (DifficultyLevel.HARD, 1500.0),
    ],
)
def test_rival_treasury_grows_with_difficulty(
    difficulty: DifficultyLevel, expected_gold: float
):
    assert starting_resources(difficulty, False)[ResourceType.GOLD] == expected_gold


def test_normal_difficulty_gives_both_sides_the_same_treasury():
    """На нормальной сложности форы нет ни у кого."""
    player = starting_resources(DifficultyLevel.NORMAL, True)
    rival = starting_resources(DifficultyLevel.NORMAL, False)

    assert player == rival


def test_starting_resources_cover_all_three_resources():
    treasury = starting_resources(DifficultyLevel.NORMAL, True)

    assert set(treasury) == set(ResourceType)


def test_starting_resources_return_a_copy():
    """Партия тратит эти деньги: таблица констант должна остаться целой."""
    first = starting_resources(DifficultyLevel.EASY, True)
    first[ResourceType.GOLD] = 0.0

    assert starting_resources(DifficultyLevel.EASY, True)[ResourceType.GOLD] == 1500.0
