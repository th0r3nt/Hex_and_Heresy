"""
Дальность обзора на тактической сетке.

Правило простое: в ясные серые часы поле просматривается целиком, ночь
роняет обзор до ближнего круга, а непогода срезает его сверх того. Ослепнуть
полностью нельзя ни при каком сочетании условий.
"""

import pytest

from src.back.l01_domain.combat.constants import (
    BATTLE_MAP_DIMENSIONS,
    DAY_VISION_RANGE_CELLS,
    MIN_VISION_RANGE_CELLS,
    NIGHT_VISION_RANGE_CELLS,
    TimeOfDay,
    WeatherCondition,
)
from src.back.l01_domain.combat.visibility import (
    base_vision_range_cells,
    resolve_visibility_range_cells,
    weather_visibility_penalty_cells,
)


# ==================================================================
# БАЗОВАЯ ВИДИМОСТЬ ПО ВРЕМЕНИ СУТОК
# ==================================================================


class TestBaseVisionRange:
    def test_grey_hours_cover_the_whole_field(self):
        """
        Днем базовый обзор не меньше самой большой карты: без погодных
        штрафов бой просматривается от края до края.
        """
        largest_side = max(
            max(width, height) for width, height in BATTLE_MAP_DIMENSIONS.values()
        )

        assert base_vision_range_cells(TimeOfDay.GREY_HOURS) >= largest_side

    def test_neon_hours_drop_vision_to_the_near_circle(self):
        assert base_vision_range_cells(TimeOfDay.NEON_HOURS) == NIGHT_VISION_RANGE_CELLS


# ==================================================================
# ШТРАФЫ ПОГОДЫ
# ==================================================================


class TestWeatherPenalty:
    def test_clear_sky_takes_nothing(self):
        assert weather_visibility_penalty_cells(WeatherCondition.CLEAR) == 0

    @pytest.mark.parametrize(
        "weather, expected",
        [
            (WeatherCondition.CLOUDY, 1),
            (WeatherCondition.SNOWFALL, 2),
            (WeatherCondition.ASH_STORM, 3),
            (WeatherCondition.TOXIC_MIST, 3),
        ],
    )
    def test_bad_weather_takes_its_cells(
        self, weather: WeatherCondition, expected: int
    ):
        """Штраф берется из тех же эффектов, что накладывает сама погода."""
        assert weather_visibility_penalty_cells(weather) == expected

    def test_rain_blinds_nobody(self):
        """Дождь мочит порох, но видеть не мешает."""
        assert weather_visibility_penalty_cells(WeatherCondition.HEAVY_RAIN) == 0


# ==================================================================
# ИТОГОВАЯ ВИДИМОСТЬ БОЯ
# ==================================================================


class TestResolvedVisibility:
    def test_clear_grey_hours_give_full_range(self):
        resolved = resolve_visibility_range_cells(
            TimeOfDay.GREY_HOURS, WeatherCondition.CLEAR
        )

        assert resolved == DAY_VISION_RANGE_CELLS

    def test_neon_hours_cut_range_to_three_cells(self):
        resolved = resolve_visibility_range_cells(
            TimeOfDay.NEON_HOURS, WeatherCondition.CLEAR
        )

        assert resolved == NIGHT_VISION_RANGE_CELLS

    def test_ash_storm_shortens_the_day(self):
        """Пепельная буря режет дневной обзор на три клетки."""
        resolved = resolve_visibility_range_cells(
            TimeOfDay.GREY_HOURS, WeatherCondition.ASH_STORM
        )

        assert resolved == DAY_VISION_RANGE_CELLS - 3

    def test_toxic_mist_at_night_leaves_the_bare_minimum(self):
        """
        Ночь плюс токсичный туман забирают весь запас, но отряд все равно
        различает соседнюю клетку: иначе бой встал бы намертво.
        """
        resolved = resolve_visibility_range_cells(
            TimeOfDay.NEON_HOURS, WeatherCondition.TOXIC_MIST
        )

        assert resolved == MIN_VISION_RANGE_CELLS

    @pytest.mark.parametrize("time_of_day", list(TimeOfDay))
    @pytest.mark.parametrize("weather", list(WeatherCondition))
    def test_vision_is_never_zero(
        self, time_of_day: TimeOfDay, weather: WeatherCondition
    ):
        assert (
            resolve_visibility_range_cells(time_of_day, weather)
            >= MIN_VISION_RANGE_CELLS
        )
