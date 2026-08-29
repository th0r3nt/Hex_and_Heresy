"""
Дальность обзора отряда на тактической сетке.

Туман войны в бою - это не отдельный слой карты, а одно число: насколько
далеко отряд вообще что-то различает. Дальше этой границы стрелок не видит
цели, и его выстрел не состоится, даже если оружие бьет туда с запасом.

Штрафы погоды не выдумываются заново: они берутся из тех же боевых эффектов,
что накладывает на бой сама погода (weather.py), - иначе таблица штрафов
разъехалась бы на два места сразу.
"""

from src.back.l01_domain.combat.constants import (
    DAY_VISION_RANGE_CELLS,
    MIN_VISION_RANGE_CELLS,
    NIGHT_VISION_RANGE_CELLS,
    TimeOfDay,
    WeatherCondition,
)
from src.back.l01_domain.combat.weather import get_weather_combat_effects
from src.back.l01_domain.common import StatName


def base_vision_range_cells(time_of_day: TimeOfDay) -> int:
    """
    Базовая дальность обзора до поправки на погоду.

    В серые часы поле просматривается целиком, в неоновые - только ближний
    круг: радиационное свечение неба света не дает.
    """
    if time_of_day == TimeOfDay.NEON_HOURS:
        return NIGHT_VISION_RANGE_CELLS
    return DAY_VISION_RANGE_CELLS


def weather_visibility_penalty_cells(weather: WeatherCondition) -> int:
    """
    Насколько клеток погода срезает обзор (положительное число - штраф).

    Пепельная буря и токсичный туман забирают по три клетки, снегопад - две,
    пасмурность - одну; ясное небо не забирает ничего.
    """
    penalty = 0.0

    for effect in get_weather_combat_effects(weather):
        for modifier in effect.modifiers:
            if modifier.stat_name == StatName.VISIBILITY_RANGE_CELLS:
                penalty += modifier.value

    # Модификаторы записаны как штрафы со знаком минус - возвращаем модуль
    return int(-penalty) if penalty < 0 else 0


def resolve_visibility_range_cells(
    time_of_day: TimeOfDay, weather: WeatherCondition
) -> int:
    """
    Итоговая дальность обзора отряда в клетках для текущих условий боя.

    Ослепнуть до нуля нельзя: соседнюю клетку отряд различает и ночью в
    токсичном тумане, иначе бой встал бы намертво.
    """
    raw = base_vision_range_cells(time_of_day) - weather_visibility_penalty_cells(weather)
    return max(MIN_VISION_RANGE_CELLS, raw)
