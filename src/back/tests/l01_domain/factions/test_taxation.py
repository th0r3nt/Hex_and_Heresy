"""
Тесты налоговой ставки фракции: границы ползунка, режимы налогообложения
и расчет налогооблагаемой базы.
"""

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions.factions import InvalidTaxRateError
from src.back.l01_domain.factions.constants import (
    BASE_TAX_HQ_PER_LEVEL,
    BASE_TAX_RATE,
    BASE_TAX_ZONE_PER_LEVEL,
    MAX_TAX_RATE,
    MIN_TAX_RATE,
    TaxPolicyBand,
    resolve_tax_band,
)
from src.back.l01_domain.factions.models.buildings import Headquarters, RegionalHall
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord


@pytest.fixture
def faction() -> Faction:
    lord = Lord(faction_id="test_fac", name="Лорд", title="Барон")
    hq = Headquarters(faction_id="test_fac", name="Цитадель", level=2)
    return Faction(
        id="test_fac",
        race=FactionRace.HUMANS,
        name="Фракция",
        lord=lord,
        headquarters=hq,
    )


# ==================================================================
# ПОЛЗУНОК СТАВКИ
# ==================================================================


class TestTaxRateSlider:
    def test_new_faction_starts_at_baseline_rate(self, faction: Faction):
        assert faction.tax_rate == BASE_TAX_RATE
        assert faction.tax_band == TaxPolicyBand.BASELINE

    @pytest.mark.parametrize("rate", [MIN_TAX_RATE, 0.35, 1.0, 1.75, MAX_TAX_RATE])
    def test_rate_inside_slider_is_accepted(self, faction: Faction, rate: float):
        faction.set_tax_rate(rate)
        assert faction.tax_rate == rate

    @pytest.mark.parametrize("rate", [-0.1, 2.1, 10.0])
    def test_rate_outside_slider_is_rejected(self, faction: Faction, rate: float):
        with pytest.raises(InvalidTaxRateError):
            faction.set_tax_rate(rate)
        assert faction.tax_rate == BASE_TAX_RATE

    def test_broken_save_with_impossible_rate_is_rejected_on_load(self):
        lord = Lord(faction_id="test_fac", name="Лорд", title="Барон")
        hq = Headquarters(faction_id="test_fac", name="Цитадель")
        with pytest.raises(InvalidTaxRateError):
            Faction(
                id="test_fac",
                race=FactionRace.HUMANS,
                name="Фракция",
                lord=lord,
                headquarters=hq,
                tax_rate=5.0,
            )


# ==================================================================
# РЕЖИМЫ НАЛОГООБЛОЖЕНИЯ
# ==================================================================


class TestTaxPolicyBands:
    @pytest.mark.parametrize(
        "rate, expected_band",
        [
            (0.0, TaxPolicyBand.HOLIDAY),
            (0.1, TaxPolicyBand.REDUCED),
            (0.9, TaxPolicyBand.REDUCED),
            (1.0, TaxPolicyBand.BASELINE),
            (1.1, TaxPolicyBand.RAISED),
            (1.4, TaxPolicyBand.RAISED),
            (1.5, TaxPolicyBand.PREDATORY),
            (2.0, TaxPolicyBand.PREDATORY),
        ],
    )
    def test_rate_falls_into_expected_band(self, rate: float, expected_band: TaxPolicyBand):
        assert resolve_tax_band(rate).band == expected_band

    def test_tax_holiday_lifts_morale_and_never_riots(self):
        effects = resolve_tax_band(0.0)
        assert effects.morale_delta(0.0) == 5.0
        assert effects.strike_chance == 0.0
        assert effects.riot_chance(0.0) == 0.0

    def test_baseline_rate_leaves_society_untouched(self):
        effects = resolve_tax_band(1.0)
        assert effects.morale_delta(1.0) == 0.0
        assert effects.strike_chance == 0.0
        assert effects.riot_chance(1.0) == 0.0

    def test_raised_taxes_hurt_morale_and_risk_strikes(self):
        effects = resolve_tax_band(1.1)
        assert effects.morale_delta(1.1) == pytest.approx(-3.0)
        assert effects.morale_delta(1.4) == pytest.approx(-8.0)
        assert effects.strike_chance == pytest.approx(0.05)

    def test_predatory_taxes_scale_penalty_with_greed(self):
        effects = resolve_tax_band(2.0)
        assert effects.morale_delta(1.5) == pytest.approx(-10.0)
        assert effects.morale_delta(2.0) == pytest.approx(-20.0)
        assert effects.riot_chance(1.5) == pytest.approx(0.10)
        assert effects.riot_chance(2.0) == pytest.approx(0.20)

    def test_effects_change_smoothly_inside_a_band(self):
        """Ползунок непрерывный: середина режима дает промежуточный штраф."""
        effects = resolve_tax_band(1.75)
        assert effects.morale_delta(1.75) == pytest.approx(-15.0)
        assert effects.riot_chance(1.75) == pytest.approx(0.15)


# ==================================================================
# НАЛОГООБЛАГАЕМАЯ БАЗА
# ==================================================================


class TestTaxableBase:
    def test_base_grows_with_citadel_level(self, faction: Faction):
        assert faction.taxable_base_gold == pytest.approx(2 * BASE_TAX_HQ_PER_LEVEL)

        faction.headquarters.upgrade()
        assert faction.taxable_base_gold == pytest.approx(3 * BASE_TAX_HQ_PER_LEVEL)

    def test_allied_halls_add_periphery_tax(self, faction: Faction):
        faction.gain_zone("zone_01")
        faction.add_regional_hall(
            RegionalHall(faction_id=faction.id, zone_id="zone_01", name="Ратуша", level=2)
        )

        expected = 2 * BASE_TAX_HQ_PER_LEVEL + 2 * BASE_TAX_ZONE_PER_LEVEL
        assert faction.taxable_base_gold == pytest.approx(expected)

    def test_one_hall_per_zone(self, faction: Faction):
        for _ in range(2):
            faction.add_regional_hall(
                RegionalHall(faction_id=faction.id, zone_id="zone_01", name="Ратуша")
            )
        assert len(faction.regional_halls) == 1

    def test_lost_zone_stops_paying_taxes(self, faction: Faction):
        faction.gain_zone("zone_01")
        faction.add_regional_hall(
            RegionalHall(faction_id=faction.id, zone_id="zone_01", name="Ратуша")
        )

        faction.lose_zone("zone_01")

        assert faction.get_regional_hall("zone_01") is None
        assert faction.taxable_base_gold == pytest.approx(2 * BASE_TAX_HQ_PER_LEVEL)

    def test_income_is_base_scaled_by_the_slider(self, faction: Faction):
        faction.set_tax_rate(1.5)
        assert faction.tax_income_gold == pytest.approx(faction.taxable_base_gold * 1.5)

    def test_tax_holiday_brings_nothing_to_the_treasury(self, faction: Faction):
        faction.set_tax_rate(0.0)
        assert faction.tax_income_gold == 0.0
