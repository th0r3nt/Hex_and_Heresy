"""
Тесты калькулятора стоимости кастомного снаряжения.

Цена одной штуки складывается из базы тира, технологических множителей
за теги и наценки за индивидуальный заказ.
"""

import pytest

from src.back.l01_domain.army.constants import EquipmentTag
from src.back.l02_services.mechanics.gunsmith.validation.economy import (
    CUSTOM_PREMIUM_MULTIPLIER,
    TIER_BASE_GOLD,
    TIER_BASE_MATERIAL,
    EquipmentEconomist,
)


def _expected(base: float, *multipliers: float) -> float:
    """
    Ожидаемая цена: множители тегов накручиваются на базу тира, и только
    потом сверху ложится наценка за индивидуальный заказ.
    """
    price = base
    for multiplier in multipliers:
        price *= multiplier
    return round(price * CUSTOM_PREMIUM_MULTIPLIER, 1)


# ====================================================
# База тира
# ====================================================


class TestTierBaseCost:
    @pytest.mark.parametrize(
        "tier, gold, material",
        [
            (1, 5.0, 7.5),
            (2, 12.5, 18.8),
            (3, 31.2, 37.5),
            (4, 62.5, 75.0),
            (5, 125.0, 150.0),
            (6, 312.5, 375.0),
        ],
    )
    def test_plain_item_costs_tier_base_plus_premium(
        self, tier: int, gold: float, material: float
    ):
        """Предмет без тегов стоит базу тира, умноженную на наценку за кастом."""
        assert EquipmentEconomist.calculate_cost(tier, []) == (gold, material)

    def test_premium_is_actually_charged(self):
        """Работа мастера по индивидуальному заказу дороже серийной."""
        gold, material = EquipmentEconomist.calculate_cost(4, [])

        assert gold == pytest.approx(TIER_BASE_GOLD[4] * CUSTOM_PREMIUM_MULTIPLIER, abs=0.1)
        assert material == pytest.approx(
            TIER_BASE_MATERIAL[4] * CUSTOM_PREMIUM_MULTIPLIER, abs=0.1
        )

    def test_cost_grows_with_tier(self):
        golds = [EquipmentEconomist.calculate_cost(tier, [])[0] for tier in sorted(TIER_BASE_GOLD)]

        assert golds == sorted(golds)
        assert len(set(golds)) == len(golds)

    def test_unknown_tier_falls_back_to_a_minimal_price(self):
        """Тир вне таблицы не роняет расчет: предмет просто выходит дешевым."""
        assert EquipmentEconomist.calculate_cost(99, []) == (6.2, 10.0)


# ====================================================
# Технологические теги
# ====================================================


class TestTagMultipliers:
    def test_resonite_hits_both_gold_and_material(self):
        """Резонит дорог сам по себе и крайне ресурсоемок в обработке."""
        gold, material = EquipmentEconomist.calculate_cost(2, [EquipmentTag.RESONITE_POWERED])

        assert gold == _expected(TIER_BASE_GOLD[2], 1.5)
        assert material == _expected(TIER_BASE_MATERIAL[2], 2.0)

    def test_silver_only_raises_the_price_in_gold(self):
        """Чистое серебро бьет по казне, но не по складам."""
        _, plain_material = EquipmentEconomist.calculate_cost(3, [])
        gold, material = EquipmentEconomist.calculate_cost(3, [EquipmentTag.SILVER])

        assert gold == _expected(TIER_BASE_GOLD[3], 2.5)
        assert material == plain_material

    def test_blackpowder_only_eats_material(self):
        """Порох и литье стволов - это расход материалов, а не золота."""
        plain_gold, _ = EquipmentEconomist.calculate_cost(2, [])
        gold, material = EquipmentEconomist.calculate_cost(2, [EquipmentTag.BLACKPOWDER])

        assert gold == plain_gold
        assert material == _expected(TIER_BASE_MATERIAL[2], 1.5)

    def test_heavy_only_eats_material(self):
        """На тяжелые латы и двуручники уходит больше стали."""
        plain_gold, _ = EquipmentEconomist.calculate_cost(4, [])
        gold, material = EquipmentEconomist.calculate_cost(4, [EquipmentTag.HEAVY])

        assert gold == plain_gold
        assert material == _expected(TIER_BASE_MATERIAL[4], 1.3)

    def test_multipliers_stack(self):
        """Тяжелый пороховой ствол собирает оба материальных множителя."""
        gold, material = EquipmentEconomist.calculate_cost(
            3, [EquipmentTag.HEAVY, EquipmentTag.BLACKPOWDER]
        )

        assert gold == _expected(TIER_BASE_GOLD[3])
        assert material == _expected(TIER_BASE_MATERIAL[3], 1.3, 1.5)

    def test_full_house_of_expensive_tags(self):
        """Серебряный резонитовый доспех тира 5 - разорительная затея."""
        gold, material = EquipmentEconomist.calculate_cost(
            5,
            [EquipmentTag.RESONITE_POWERED, EquipmentTag.SILVER, EquipmentTag.HEAVY],
        )

        assert gold == _expected(TIER_BASE_GOLD[5], 1.5, 2.5)
        assert material == _expected(TIER_BASE_MATERIAL[5], 2.0, 1.3)

    def test_neutral_tags_do_not_change_the_price(self):
        """Хват и лорные пометки на смету не влияют."""
        plain = EquipmentEconomist.calculate_cost(3, [])
        tagged = EquipmentEconomist.calculate_cost(
            3, [EquipmentTag.TWO_HANDED, EquipmentTag.BRACEABLE, EquipmentTag.CURSED]
        )

        assert tagged == plain
