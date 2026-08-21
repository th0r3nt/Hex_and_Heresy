import pytest

from src.back.l01_domain.combat.constants import WeatherCondition
from src.back.l01_domain.combat.weather import get_weather_combat_effects
from src.back.l01_domain.common import StatName


class TestGetWeatherCombatEffects:
    def test_clear_weather_has_no_effects(self):
        assert get_weather_combat_effects(WeatherCondition.CLEAR) == []

    @pytest.mark.parametrize(
        "condition",
        [
            WeatherCondition.HEAVY_RAIN,
            WeatherCondition.SNOWFALL,
            WeatherCondition.CLOUDY,
            WeatherCondition.ASH_STORM,
            WeatherCondition.TOXIC_MIST,
            WeatherCondition.MAGNETIC_STORM,
        ],
    )
    def test_non_clear_weather_returns_at_least_one_effect(self, condition):
        assert len(get_weather_combat_effects(condition)) >= 1

    def test_effect_ids_are_unique_within_a_condition(self):
        effects = get_weather_combat_effects(WeatherCondition.HEAVY_RAIN)
        ids = [e.id for e in effects]
        assert len(ids) == len(set(ids))

    def test_magnetic_storm_disables_magic_and_boosts_human_morale(self):
        effects = get_weather_combat_effects(WeatherCondition.MAGNETIC_STORM)
        stat_names = {mod.stat_name for e in effects for mod in e.modifiers}

        assert StatName.MAGIC_DISABLED in stat_names
        assert StatName.MORALE in stat_names