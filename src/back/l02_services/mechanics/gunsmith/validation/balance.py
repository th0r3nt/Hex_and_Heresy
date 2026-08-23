"""
Балансировщик кастомного снаряжения.
Конвертирует абстрактные приоритеты от LLM в жесткие доменные статы.
"""

import math
from typing import Final

from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.l02_services.mechanics.gunsmith.crafting import StatPriorities

# Базовый бюджет очков на каждый тир снаряжения
TIER_BASE_BUDGET: Final[dict[int, float]] = {
    1: 15.0,
    2: 25.0,
    3: 40.0,
    4: 65.0,
    5: 100.0,
    6: 150.0,
}

# "Стоимость" 1 единицы характеристики в очках бюджета
STAT_COST: Final[dict[str, float]] = {
    "damage": 1.5,  # 1 ед. урона обходится в 1.5 очко бюджета
    "armor_piercing": 2.0,  # 1 ед. пробития брони обходится в 2 очка (бронебойность дорогая)
    "armor_bonus": 1.5,  # 1 ед. брони обходится в 1.5 очка
    "range_hexes": 5.0,  # 1 дополнительный гекс дальности обходится в 5 очков
}

# Сколько дополнительного бюджета дает 1 уровень штрафа (от 0 до 10)
TRADEOFF_BUDGET_GAIN: Final[float] = 2.5


class EquipmentBalancer:
    """
    Инкапсулирует математику превращения приоритетов нейросети в доменные статы.
    """

    @staticmethod
    def normalize_stats(tier: int, priorities: StatPriorities) -> EquipmentStats:
        """
        Главный метод нормализации. Рассчитывает доступный бюджет и распределяет его.
        """

        # 1. Считаем доступный бюджет
        base_budget = TIER_BASE_BUDGET.get(tier, 10.0)
        bonus_budget = (
            priorities.heavy_weight_tradeoff + priorities.clunkiness_tradeoff
        ) * TRADEOFF_BUDGET_GAIN
        total_budget = base_budget + bonus_budget

        # 2. Оцениваем суммарный вес приоритетов
        total_priority = (
            priorities.damage
            + priorities.armor_piercing
            + priorities.armor_bonus
            + priorities.range_hexes
        )

        # Защита от нулевого ответа LLM
        if total_priority == 0:
            return EquipmentBalancer._apply_tradeoffs(EquipmentStats(), priorities)

        # 3. Распределяем бюджет пропорционально выставленным приоритетам
        damage_budget = total_budget * (priorities.damage / total_priority)
        ap_budget = total_budget * (priorities.armor_piercing / total_priority)
        armor_budget = total_budget * (priorities.armor_bonus / total_priority)
        range_budget = total_budget * (priorities.range_hexes / total_priority)

        # 4. Покупаем реальные статы за распределенный бюджет
        final_damage = round(damage_budget / STAT_COST["damage"], 1)
        final_ap = round(ap_budget / STAT_COST["armor_piercing"], 1)
        final_armor = round(armor_budget / STAT_COST["armor_bonus"], 1)

        # Дальность всегда равна 1 (ближний бой). Дополнительная дальность покупается.
        extra_range = math.floor(range_budget / STAT_COST["range_hexes"])
        final_range = 1 + extra_range

        stats = EquipmentStats(
            damage=final_damage,
            armor_piercing=final_ap,
            armor_bonus=final_armor,
            range_hexes=final_range,
        )

        # 5. Жестко применяем штрафы за полученный бонусный бюджет
        return EquipmentBalancer._apply_tradeoffs(stats, priorities)

    @staticmethod
    def _apply_tradeoffs(stats: EquipmentStats, priorities: StatPriorities) -> EquipmentStats:
        """
        Превращает заявленные нейросетью трейд-оффы в реальные дебаффы (скорость, инициатива).
        """
        # Один уровень тяжести = -2% скорости и +0.2 расхода выносливости
        speed_mod = -(priorities.heavy_weight_tradeoff * 0.02)
        stamina_drain = priorities.heavy_weight_tradeoff * 0.2

        # Один уровень неповоротливости = -1 к инициативе
        init_mod = -priorities.clunkiness_tradeoff

        return stats.model_copy(
            update={
                "speed_modifier": round(speed_mod, 2),
                "stamina_drain_per_turn": round(stamina_drain, 1),
                "initiative_modifier": init_mod,
            }
        )
