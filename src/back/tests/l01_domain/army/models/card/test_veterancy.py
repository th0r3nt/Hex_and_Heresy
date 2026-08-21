"""
Тесты для src/back/l01_domain/army/models/card/veterancy.py
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.army.models.card.veterancy import (
    MechanicalModifier,
    VeterancyStatus,
)
from src.back.l01_domain.common import StatName


class TestMechanicalModifier:
    def test_percentage_flag_defaults_to_false(self):
        modifier = MechanicalModifier(stat_name=StatName.MORALE, value=2.0)

        assert modifier.is_percentage is False

    def test_can_represent_percentage_bonus(self):
        modifier = MechanicalModifier(stat_name=StatName.DAMAGE, value=15.0, is_percentage=True)

        assert modifier.is_percentage is True
        assert modifier.value == 15.0


class TestVeterancyStatus:
    def test_fresh_squad_is_not_named(self):
        status = VeterancyStatus()

        assert status.is_named is False
        assert status.commander_name is None
        assert status.squad_nickname is None
        assert status.upkeep_gold_multiplier == 1.0

    def test_upkeep_multiplier_cannot_go_below_one(self):
        # Ветераны могут требовать больше жалования, но не меньше базового.
        with pytest.raises(ValidationError):
            VeterancyStatus(upkeep_gold_multiplier=0.5)

    def test_promote_marks_squad_as_named(self):
        # Сценарий "Давид и Голиаф" из veterancy.md
        status = VeterancyStatus()
        modifier = MechanicalModifier(stat_name=StatName.MORALE, value=2.0)

        status.promote(
            commander_name="Маркус",
            squad_nickname="Грязные стрелки Маркуса",
            trait_name="Высокомерные",
            lore="Расстреляли Огра, пока рыцари отступали.",
            modifier=modifier,
        )

        assert status.is_named is True
        assert status.commander_name == "Маркус"
        assert status.squad_nickname == "Грязные стрелки Маркуса"
        assert status.trait_name == "Высокомерные"
        assert status.modifier is modifier

    def test_promote_without_mechanical_modifier_is_allowed(self):
        # Не каждый подвиг обязан давать числовой бафф.
        status = VeterancyStatus()

        status.promote(
            commander_name="Ганс",
            squad_nickname="Одноглазые егеря",
            trait_name="Циничные",
            lore="Пережили резню с гоблинами.",
        )

        assert status.is_named is True
        assert status.modifier is None


class TestAccumulateKills:
    def test_accumulation_below_threshold_returns_false(self):
        status = VeterancyStatus()

        crossed = status.accumulate_kills(100.0)

        assert crossed is False
        assert status.accumulated_kill_weight == 100.0

    def test_crossing_threshold_returns_true_exactly_once(self):
        status = VeterancyStatus()
        status.accumulate_kills(499.0)

        crossed_now = status.accumulate_kills(1.0)  # ровно 500.0
        assert crossed_now is True
        assert status.accumulated_kill_weight == 500.0

        # Повторный вызов после пересечения порога больше не сигналит
        crossed_again = status.accumulate_kills(50.0)
        assert crossed_again is False

    def test_zero_or_negative_weight_is_noop(self):
        status = VeterancyStatus()

        assert status.accumulate_kills(0.0) is False
        assert status.accumulate_kills(-10.0) is False
        assert status.accumulated_kill_weight == 0.0


class TestAccumulateService:
    def test_accumulation_below_threshold_returns_false(self):
        status = VeterancyStatus()

        crossed = status.accumulate_service(30.0)

        assert crossed is False
        assert status.accumulated_service_days == 30.0

    def test_zero_or_negative_days_is_noop(self):
        status = VeterancyStatus()

        assert status.accumulate_service(0.0) is False
        assert status.accumulate_service(-1.0) is False
        assert status.accumulated_service_days == 0.0


class TestVeterancyAccumulatorsAreIndependent:
    def test_crossing_kill_threshold_does_not_affect_service_accumulator(self):
        """Два триггера повышения не должны влиять друг на друга."""
        status = VeterancyStatus()
        status.accumulate_kills(600.0)  # сразу за порогом убийств

        assert status.accumulated_service_days == 0.0
        assert status.accumulate_service(60.0) is True  # служба считается с нуля
