"""
Тесты для src/back/l01_domain/army/models/card/veterancy.py
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.army.models.card.veterancy import (
    MechanicalModifier,
    VeterancyStatus,
)


class TestMechanicalModifier:
    def test_percentage_flag_defaults_to_false(self):
        modifier = MechanicalModifier(stat_name="morale", value=2.0)

        assert modifier.is_percentage is False

    def test_can_represent_percentage_bonus(self):
        modifier = MechanicalModifier(stat_name="damage", value=15.0, is_percentage=True)

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
        modifier = MechanicalModifier(stat_name="morale", value=2.0)

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
