"""
Калькулятор стоимости кастомной экипировки.
"""

from typing import Final
from src.back.l01_domain.army.constants import EquipmentTag

# Базовая стоимость производства предмета в зависимости от его тира
TIER_BASE_GOLD: Final[dict[int, float]] = {
    1: 4.0,
    2: 10.0,
    3: 25.0,
    4: 50.0,
    5: 100.0,
    6: 250.0,
}

TIER_BASE_MATERIAL: Final[dict[int, float]] = {
    1: 6.0,
    2: 15.0,
    3: 30.0,
    4: 60.0,
    5: 120.0,
    6: 300.0,
}

# Наценка за индивидуальный заказ у Оружейника
CUSTOM_PREMIUM_MULTIPLIER: Final[float] = 1.25


class EquipmentEconomist:
    """
    Рассчитывает стоимость одной единицы снаряжения (в золоте и материалах).
    """

    @staticmethod
    def calculate_cost(tier: int, tags: list[EquipmentTag]) -> tuple[float, float]:
        gold = TIER_BASE_GOLD.get(tier, 5.0)
        material = TIER_BASE_MATERIAL.get(tier, 8.0)

        # Технологические множители
        if EquipmentTag.RESONITE_POWERED in tags:
            gold *= 1.5
            material *= 2.0  # Резонит крайне ресурсоемок в обработке
        if EquipmentTag.SILVER in tags:
            gold *= 2.5  # Чистое серебро очень дорогое
        if EquipmentTag.BLACKPOWDER in tags:
            material *= 1.5  # Производство пороха и литье стволов требует ресурсов
        if EquipmentTag.HEAVY in tags:
            material *= 1.3  # Больше стали/древесины на тяжелые латы и двуручники

        # Применяем наценку за кастом
        final_gold = round(gold * CUSTOM_PREMIUM_MULTIPLIER, 1)
        final_material = round(material * CUSTOM_PREMIUM_MULTIPLIER, 1)

        return final_gold, final_material
