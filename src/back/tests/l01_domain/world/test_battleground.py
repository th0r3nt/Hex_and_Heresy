"""
Тесты для src/back/l01_domain/world/models/battleground.py
"""

from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.battleground import (
    BattlefieldCorpsePile,
    BattlefieldLootSite,
)


class TestBattlefieldLootSite:
    def _make_site(self) -> BattlefieldLootSite:
        return BattlefieldLootSite(
            hex_coordinates=HexCoordinates.from_axial(1, 0),
            origin_battle_id="battle_123",
            salvageable_equipment={"human_arquebus_02": 15, "human_cuirass_02": 10},
            residual_resonite=50.0,
            corpses=[
                BattlefieldCorpsePile(
                    race=FactionRace.HUMANS, size_category=UnitSizeCategory.MEDIUM, count=25
                )
            ],
            ticks_remaining=3,
        )

    def test_claim_equipment_partially_and_fully(self):
        site = self._make_site()

        taken = site.claim_equipment("human_arquebus_02", 5)
        assert taken == 5
        assert site.salvageable_equipment["human_arquebus_02"] == 10

        taken_all = site.claim_equipment("human_arquebus_02", 20)
        assert taken_all == 10
        assert "human_arquebus_02" not in site.salvageable_equipment

    def test_siphon_resonite(self):
        site = self._make_site()

        resonite = site.siphon_resonite()
        assert resonite == 50.0
        assert site.residual_resonite == 0.0

    def test_decay_leads_to_depletion(self):
        site = self._make_site()
        assert not site.is_depleted

        site.decay_tick()
        site.decay_tick()
        site.decay_tick()

        assert site.ticks_remaining == 0
        assert site.is_depleted
