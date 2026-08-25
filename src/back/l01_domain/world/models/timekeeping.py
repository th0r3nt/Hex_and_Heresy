"""
Модель игрового времени и счета циклов в Эпоху застоя.
"""

from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.combat.constants import TimeOfDay
from src.back.l01_domain.world.constants import (
    DAYS_PER_CYCLE,
    DEFAULT_HOURS_PER_TICK,
    GREY_HOURS_COUNT,
    HOURS_PER_DAY,
)

from src.back.l01_domain.exceptions.timekeeping import TimeRewindForbiddenError

class GameTime(BaseModel):
    """
    Счетчик времени игрового мира.
    Управляет конвертацией тактов в часы, сутки и циклы.
    """

    model_config = ConfigDict(validate_assignment=True)

    total_ticks: int = Field(
        default=0, ge=0, description="Общее число прошедших глобальных ходов"
    )
    hours_per_tick: int = Field(
        default=DEFAULT_HOURS_PER_TICK,
        gt=0,
        le=HOURS_PER_DAY,
        description="Сколько внутриигровых часов проходит за один такт",
    )

    current_hour: int = Field(
        default=0, ge=0, lt=HOURS_PER_DAY, description="Текущий час суток (0..27)"
    )
    current_day: int = Field(
        default=1, ge=1, le=DAYS_PER_CYCLE, description="Текущий день цикла (1..300)"
    )
    current_year: int = Field(default=1, ge=1, description="Текущий год")

    @property
    def time_of_day(self) -> TimeOfDay:
        """
        Определяет текущую световую фазу суток: серые или неоновые часы.
        """
        if self.current_hour < GREY_HOURS_COUNT:
            return TimeOfDay.GREY_HOURS
        return TimeOfDay.NEON_HOURS

    @property
    def is_neon_hours(self) -> bool:
        """Флаг наступления неоновых часов (ночи с радиационным свечением)."""
        return self.time_of_day == TimeOfDay.NEON_HOURS

    def advance_ticks(self, ticks: int = 1) -> None:
        """
        Продвигает игровое время вперед на заданное количество тактов.
        Корректно производит перенос часов, дней и циклов.
        """
        if ticks < 0:
            raise TimeRewindForbiddenError(ticks)
        if ticks == 0:
            return

        self.total_ticks += ticks
        total_added_hours = ticks * self.hours_per_tick

        new_total_hours = self.current_hour + total_added_hours
        added_days = new_total_hours // HOURS_PER_DAY
        self.current_hour = new_total_hours % HOURS_PER_DAY

        if added_days > 0:
            # Дни нумеруются с 1 по DAYS_PER_CYCLE
            zero_based_day = (self.current_day - 1) + added_days
            added_cycles = zero_based_day // DAYS_PER_CYCLE
            self.current_day = (zero_based_day % DAYS_PER_CYCLE) + 1
            self.current_year += added_cycles

    def format_timestamp(self) -> str:
        """
        Возвращает строковое представление игрового времени для интерфейса.
        """
        phase_label = "серые часы" if not self.is_neon_hours else "неоновые часы"
        return f"Год {self.current_year}, День {self.current_day}, {self.current_hour:02d}:00 ({phase_label})"
