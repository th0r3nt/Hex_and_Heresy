"""
Конвертация погодного условия боя в конкретные боевые эффекты (CombatEffect).

Эффекты асимметричны по расам (магнитная буря бьёт по магии эльфов,
но поднимает мораль людям) - сама фабрика этого не знает, она лишь
формирует список эффектов с говорящими id/removal_condition.
Решение, каким карточкам применять какой эффект из списка -
забота вызывающего кода в l02_services.
"""

from src.back.l01_domain.combat.constants import CombatEffectCategory, EffectStackingRule, WeatherCondition
from src.back.l01_domain.combat.models.effects import CombatEffect
from src.back.l01_domain.common import MechanicalModifier


def get_weather_combat_effects(condition: WeatherCondition) -> list[CombatEffect]:
    """Возвращает боевые эффекты, которые накладывает погодное условие на весь бой."""

    if condition == WeatherCondition.HEAVY_RAIN:
        return [
            CombatEffect(
                id="weather_rain_bow_dampening",
                name="Мокрая тетива",
                category=CombatEffectCategory.WEATHER,
                stacking_rule=EffectStackingRule.IGNORE,
                modifiers=[MechanicalModifier(stat_name="ranged_accuracy", value=-0.15, is_percentage=True)],
            ),
            CombatEffect(
                id="weather_rain_firearm_misfire",
                name="Отсыревший порох",
                category=CombatEffectCategory.WEATHER,
                stacking_rule=EffectStackingRule.IGNORE,
                modifiers=[MechanicalModifier(stat_name="firearm_misfire_chance", value=0.20, is_percentage=True)],
            ),
        ]

    if condition == WeatherCondition.SNOWFALL:
        return [
            CombatEffect(
                id="weather_snow_movement_penalty",
                name="Снежные заносы",
                category=CombatEffectCategory.WEATHER,
                stacking_rule=EffectStackingRule.IGNORE,
                modifiers=[MechanicalModifier(stat_name="movement_speed", value=-0.20, is_percentage=True)],
            ),
            CombatEffect(
                id="weather_snow_visibility",
                name="Снегопад",
                category=CombatEffectCategory.WEATHER,
                stacking_rule=EffectStackingRule.IGNORE,
                modifiers=[MechanicalModifier(stat_name="visibility_range_cells", value=-2.0)],
            ),
        ]

    if condition == WeatherCondition.CLOUDY:
        return [
            CombatEffect(
                id="weather_cloudy_visibility",
                name="Пасмурно",
                category=CombatEffectCategory.WEATHER,
                stacking_rule=EffectStackingRule.IGNORE,
                modifiers=[MechanicalModifier(stat_name="visibility_range_cells", value=-1.0)],
            ),
        ]

    if condition == WeatherCondition.ASH_STORM:
        return [
            CombatEffect(
                id="weather_ash_storm_visibility",
                name="Пепельная буря",
                category=CombatEffectCategory.WEATHER,
                stacking_rule=EffectStackingRule.IGNORE,
                modifiers=[MechanicalModifier(stat_name="visibility_range_cells", value=-3.0)],
            ),
            CombatEffect(
                id="weather_ash_storm_choking",
                name="Удушье пеплом",
                category=CombatEffectCategory.WEATHER,
                stacking_rule=EffectStackingRule.IGNORE,
                modifiers=[MechanicalModifier(stat_name="morale", value=-5.0)],
            ),
        ]

    if condition == WeatherCondition.TOXIC_MIST:
        return [
            CombatEffect(
                id="weather_toxic_mist_visibility",
                name="Токсичный туман",
                category=CombatEffectCategory.WEATHER,
                stacking_rule=EffectStackingRule.IGNORE,
                modifiers=[MechanicalModifier(stat_name="visibility_range_cells", value=-3.0)],
            ),
            CombatEffect(
                id="weather_toxic_mist_dot",
                name="Испарения Ничьей земли",
                category=CombatEffectCategory.WEATHER,
                stacking_rule=EffectStackingRule.IGNORE,
                modifiers=[MechanicalModifier(stat_name="hp_drain_per_tick", value=2.0)],
                removal_condition="не действует на носителей проклятых генов и существ с резонитовым иммунитетом",
            ),
        ]

    if condition == WeatherCondition.MAGNETIC_STORM:
        return [
            CombatEffect(
                id="weather_magnetic_storm_magic_disabled",
                name="Магнитная буря",
                category=CombatEffectCategory.WEATHER,
                stacking_rule=EffectStackingRule.IGNORE,
                modifiers=[MechanicalModifier(stat_name="magic_disabled", value=1.0)],
            ),
            CombatEffect(
                id="weather_magnetic_storm_human_morale",
                name="Небеса горят к добру",
                category=CombatEffectCategory.WEATHER,
                stacking_rule=EffectStackingRule.IGNORE,
                modifiers=[MechanicalModifier(stat_name="morale", value=10.0)],
                removal_condition="действует только на карточки расы людей",
            ),
        ]

    return []  # CLEAR