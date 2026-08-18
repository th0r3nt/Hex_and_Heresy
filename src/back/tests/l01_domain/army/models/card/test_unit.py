"""
Тесты для src/back/l01_domain/army/models/card/unit.py
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype


class TestBaseUnitStats:
    def test_requires_positive_max_hp(self):
        with pytest.raises(ValidationError):
            BaseUnitStats(max_hp=0)

    def test_defaults(self):
        stats = BaseUnitStats(max_hp=20.0)

        assert stats.base_armor == 0.0
        assert stats.base_speed == 2.0
        assert stats.base_morale == 50.0
        assert stats.base_stamina == 100.0
        assert stats.base_initiative == 10

    @pytest.mark.parametrize("morale", [-1.0, 101.0])
    def test_morale_must_stay_within_0_100(self, morale):
        with pytest.raises(ValidationError):
            BaseUnitStats(max_hp=20.0, base_morale=morale)

    def test_speed_must_be_strictly_positive(self):
        with pytest.raises(ValidationError):
            BaseUnitStats(max_hp=20.0, base_speed=0)

    def test_is_frozen(self):
        stats = BaseUnitStats(max_hp=20.0)

        with pytest.raises(ValidationError):
            stats.max_hp = 999.0


class TestUnitArchetype:
    def _make(self, **overrides) -> UnitArchetype:
        payload = dict(
            id="unit_test_pikemen",
            faction_id="humans",
            name="Тестовые копейщики",
            tier=1,
            default_unit_count=120,
            base_stats=BaseUnitStats(max_hp=15.0),
        )
        payload.update(overrides)
        return UnitArchetype(**payload)

    def test_defaults(self):
        archetype = self._make()

        assert archetype.base_upkeep_food == 1.0
        assert archetype.base_upkeep_gold == 0.0
        assert archetype.lore_description == ""

    def test_default_unit_count_must_be_positive(self):
        with pytest.raises(ValidationError):
            self._make(default_unit_count=0)

    @pytest.mark.parametrize("tier", [-1, 7])
    def test_tier_out_of_bounds_is_rejected(self, tier):
        with pytest.raises(ValidationError):
            self._make(tier=tier)

    def test_name_cannot_be_empty(self):
        with pytest.raises(ValidationError):
            self._make(name="")

    def test_is_frozen(self):
        archetype = self._make()

        with pytest.raises(ValidationError):
            archetype.tier = 3
