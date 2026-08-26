"""
Тесты балансировщика: превращение абстрактных приоритетов нейросети
в жесткие доменные статы.

Мастер не придумывает урон сам - он расставляет акценты, а бюджет тира
решает, во что эти акценты обойдутся (см. docs/game_mechanics/gunsmith.md).
"""

import pytest

from src.back.l02_services.mechanics.gunsmith.crafting import StatPriorities
from src.back.l02_services.mechanics.gunsmith.validation.balance import (
    STAT_COST,
    TIER_BASE_BUDGET,
    TRADEOFF_BUDGET_GAIN,
    EquipmentBalancer,
)


def spent_budget(stats) -> float:
    """
    Сколько очков бюджета ушло на купленные статы.
    Дальность считается сверх базового гекса ближнего боя.
    """
    return (
        stats.damage * STAT_COST["damage"]
        + stats.armor_piercing * STAT_COST["armor_piercing"]
        + stats.armor_bonus * STAT_COST["armor_bonus"]
        + (stats.range_hexes - 1) * STAT_COST["range_hexes"]
    )


# ====================================================
# Распределение бюджета
# ====================================================


class TestBudgetDistribution:
    def test_single_priority_takes_the_whole_budget(self):
        """Один приоритет - весь бюджет тира уходит в него: 15 / 1.5 = 10 урона."""
        stats = EquipmentBalancer.normalize_stats(1, StatPriorities(damage=10))

        assert stats.damage == 10.0
        assert stats.armor_piercing == 0.0
        assert stats.armor_bonus == 0.0
        assert stats.range_hexes == 1

    def test_equal_priorities_split_the_budget_in_half(self):
        """Тир 3 = 40 очков: по 20 на урон (20/1.5) и на пробитие (20/2.0)."""
        stats = EquipmentBalancer.normalize_stats(
            3, StatPriorities(damage=5, armor_piercing=5)
        )

        assert stats.damage == 13.3
        assert stats.armor_piercing == 10.0

    def test_armor_only_request_buys_armor(self):
        """Тир 4 = 65 очков: 65 / 1.5 = 43.3 брони."""
        stats = EquipmentBalancer.normalize_stats(4, StatPriorities(armor_bonus=10))

        assert stats.armor_bonus == 43.3
        assert stats.damage == 0.0

    def test_higher_tier_gets_a_bigger_budget(self):
        """Тир - это и есть цена вопроса: чем выше, тем больше статов за те же приоритеты."""
        by_tier = [
            EquipmentBalancer.normalize_stats(tier, StatPriorities(damage=10)).damage
            for tier in sorted(TIER_BASE_BUDGET)
        ]

        assert by_tier == sorted(by_tier)
        assert len(set(by_tier)) == len(by_tier)

    def test_unknown_tier_falls_back_to_a_minimal_budget(self):
        """Тир вне таблицы не роняет расчет: 10 очков резервного бюджета."""
        stats = EquipmentBalancer.normalize_stats(99, StatPriorities(damage=10))

        assert stats.damage == 6.7

    def test_budget_is_spent_without_leftovers(self):
        """Купленные статы должны стоить ровно столько, сколько дал тир."""
        stats = EquipmentBalancer.normalize_stats(
            6, StatPriorities(damage=4, armor_piercing=3, armor_bonus=2, range_hexes=1)
        )

        assert spent_budget(stats) == pytest.approx(TIER_BASE_BUDGET[6], abs=0.5)


# ====================================================
# Дальность
# ====================================================


class TestRange:
    def test_melee_range_is_the_default(self):
        """Без приоритета дальности предмет остается оружием ближнего боя."""
        stats = EquipmentBalancer.normalize_stats(5, StatPriorities(damage=10))

        assert stats.range_hexes == 1

    def test_extra_hexes_are_bought_whole(self):
        """Тир 2 = 25 очков, гекс стоит 5: +5 гексов сверх базового."""
        stats = EquipmentBalancer.normalize_stats(2, StatPriorities(range_hexes=10))

        assert stats.range_hexes == 6

    def test_budget_short_of_a_full_hex_buys_nothing(self):
        """Дальность не дробится: недобор до целого гекса просто сгорает."""
        stats = EquipmentBalancer.normalize_stats(1, StatPriorities(range_hexes=1, damage=9))

        # 15 очков * 0.1 = 1.5 очка на дальность - меньше 5 за гекс
        assert stats.range_hexes == 1


# ====================================================
# Трейд-оффы
# ====================================================


class TestTradeoffs:
    def test_tradeoffs_buy_extra_budget(self):
        """
        Готовность потяжелеть и потерять инициативу оплачивается статами:
        15 базовых + (4 + 2) * 2.5 = 30 очков вместо 15.
        """
        without = EquipmentBalancer.normalize_stats(1, StatPriorities(damage=10))
        with_tradeoffs = EquipmentBalancer.normalize_stats(
            1,
            StatPriorities(damage=10, heavy_weight_tradeoff=4, clunkiness_tradeoff=2),
        )

        assert without.damage == 10.0
        assert with_tradeoffs.damage == 20.0

    def test_weight_costs_speed_and_stamina(self):
        """Один уровень тяжести - это -2% скорости и +0.2 расхода выносливости."""
        stats = EquipmentBalancer.normalize_stats(
            1, StatPriorities(damage=10, heavy_weight_tradeoff=4)
        )

        assert stats.speed_modifier == -0.08
        assert stats.stamina_drain_per_turn == 0.8

    def test_clunkiness_costs_initiative(self):
        """Один уровень неповоротливости - это -1 к очередности хода."""
        stats = EquipmentBalancer.normalize_stats(
            1, StatPriorities(damage=10, clunkiness_tradeoff=3)
        )

        assert stats.initiative_modifier == -3
        assert stats.speed_modifier == 0.0

    def test_tradeoff_gain_matches_the_declared_rate(self):
        """Проверяем саму ставку обмена, а не только частный случай."""
        base = TIER_BASE_BUDGET[1]
        stats = EquipmentBalancer.normalize_stats(
            1, StatPriorities(damage=10, heavy_weight_tradeoff=2)
        )

        assert spent_budget(stats) == pytest.approx(base + 2 * TRADEOFF_BUDGET_GAIN, abs=0.5)


# ====================================================
# Пустой ответ модели
# ====================================================


class TestEmptyPriorities:
    def test_zero_priorities_produce_a_blank_item(self):
        """
        Модель может не расставить ни одного акцента. Делить на ноль нельзя,
        поэтому предмет выходит пустым, а не ломает расчет.
        """
        stats = EquipmentBalancer.normalize_stats(6, StatPriorities())

        assert stats.damage == 0.0
        assert stats.armor_piercing == 0.0
        assert stats.armor_bonus == 0.0
        assert stats.range_hexes == 1

    def test_tradeoffs_still_apply_to_a_blank_item(self):
        """
        Штрафы - не награда за статы, а описание самой вещи: тяжелая пустышка
        все равно замедляет носителя.
        """
        stats = EquipmentBalancer.normalize_stats(
            6, StatPriorities(heavy_weight_tradeoff=5)
        )

        assert stats.speed_modifier == -0.1
        assert stats.stamina_drain_per_turn == 1.0
        assert stats.damage == 0.0
