"""
Тесты сервиса натиска и реакций.
"""

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import (
    SPEED_CHARGE_PACE,
    SPEED_MARCH_PACE,
    ReactionType,
)
from src.back.l01_domain.combat.models.state import SquadOrder
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l02_services.turns.tactical.combat.charges import TacticalChargeService
from src.back.tests.l02_services.turns.tactical.conftest import place_squad_on_grid


class TestTacticalChargeService:
    def test_charge_resolves_and_inflicts_damage(
        self, empty_battle_state, archetype_human_sword, weapon_sword
    ):
        sq_atk = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_sword)
        sq_atk.id = "atk"
        sq_def = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_sword)
        sq_def.id = "def"
        squads = {"atk": sq_atk, "def": sq_def}

        empty_battle_state.attacker_squad_ids = ["atk"]
        empty_battle_state.defender_squad_ids = ["def"]
        place_squad_on_grid(empty_battle_state, "atk", 0, 0)
        place_squad_on_grid(empty_battle_state, "def", 2, 0)

        # Натиск от atk
        empty_battle_state.queue_order(
            SquadOrder(
                squad_id="atk", target_cell=CellCoordinates(x=2, y=0), pace=SPEED_CHARGE_PACE
            )
        )
        # Реакция def - принять удар
        empty_battle_state.queue_order(
            SquadOrder(
                squad_id="def",
                target_cell=CellCoordinates(x=2, y=0),
                reaction=ReactionType.ACCEPT_CHARGE,
            )
        )

        service = TacticalChargeService()
        reports = service.resolve_charges(empty_battle_state, squads)

        assert len(reports) == 1
        assert (
            reports[0].attacker_deaths > 0
        )  # Защитник принял удар, атакующий напоролся на копья
        assert sq_atk.state.unit_count < 100

    def test_no_charge_if_pace_is_not_charge(self, empty_battle_state, archetype_human_sword):
        sq_atk = Squad.create_new(archetype=archetype_human_sword)
        sq_atk.id = "atk"
        sq_def = Squad.create_new(archetype=archetype_human_sword)
        sq_def.id = "def"
        squads = {"atk": sq_atk, "def": sq_def}

        place_squad_on_grid(empty_battle_state, "atk", 0, 0)
        place_squad_on_grid(empty_battle_state, "def", 2, 0)

        empty_battle_state.queue_order(
            SquadOrder(
                squad_id="atk", target_cell=CellCoordinates(x=2, y=0), pace=SPEED_MARCH_PACE
            )
        )

        service = TacticalChargeService()
        reports = service.resolve_charges(empty_battle_state, squads)

        assert len(reports) == 0  # Натиск не случился
