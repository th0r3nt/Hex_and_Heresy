"""
Тесты для src/back/l01_domain/world/models/timekeeping.py
"""

import pytest

from src.back.l01_domain.combat.constants import TimeOfDay
from src.back.l01_domain.world.constants import DAYS_PER_CYCLE, GREY_HOURS_COUNT, HOURS_PER_DAY
from src.back.l01_domain.world.models.timekeeping import GameTime

from src.back.l01_domain.exceptions import TimeRewindForbiddenError


class TestGameTime:
    def test_initial_state_defaults(self):
        time = GameTime()

        assert time.total_ticks == 0
        assert time.current_hour == 0
        assert time.current_day == 1
        assert time.current_year == 1
        assert time.time_of_day == TimeOfDay.GREY_HOURS
        assert not time.is_neon_hours

    def test_time_of_day_phase_transitions(self):
        # 0..15 - серые часы
        time = GameTime(current_hour=GREY_HOURS_COUNT - 1)
        assert time.time_of_day == TimeOfDay.GREY_HOURS
        assert not time.is_neon_hours

        # 16..27 - неоновые часы
        time = GameTime(current_hour=GREY_HOURS_COUNT)
        assert time.time_of_day == TimeOfDay.NEON_HOURS
        assert time.is_neon_hours

    def test_advance_ticks_within_single_day(self):
        time = GameTime(hours_per_tick=4)
        time.advance_ticks(3)  # +12 часов

        assert time.total_ticks == 3
        assert time.current_hour == 12
        assert time.current_day == 1
        assert time.time_of_day == TimeOfDay.GREY_HOURS

    def test_advance_ticks_rollover_to_next_day(self):
        time = GameTime(current_hour=24, hours_per_tick=4)
        time.advance_ticks(1)  # 24 + 4 = 28 часов -> следующий день, 0-й час

        assert time.current_hour == 0
        assert time.current_day == 2
        assert time.current_year == 1

    def test_advance_ticks_rollover_to_next_cycle(self):
        time = GameTime(
            current_day=DAYS_PER_CYCLE,
            current_hour=HOURS_PER_DAY - 4,
            current_year=1,
            hours_per_tick=4,
        )
        time.advance_ticks(1)

        assert time.current_hour == 0
        assert time.current_day == 1
        assert time.current_year == 2

    def test_negative_ticks_raise_error(self):
        time = GameTime()
        with pytest.raises(TimeRewindForbiddenError):
            time.advance_ticks(-1)

    def test_format_timestamp_output(self):
        time = GameTime(current_hour=4, current_day=12, current_year=3)
        formatted = time.format_timestamp()

        assert "Год 3" in formatted
        assert "День 12" in formatted
        assert "04:00" in formatted
        assert "серые часы" in formatted
