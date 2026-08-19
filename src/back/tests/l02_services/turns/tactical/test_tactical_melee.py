"""
Тесты рукопашного боя, флангов и тылов.
"""

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.models.state import SquadOrder
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l02_services.turns.tactical.combat.melee import TacticalMeleeService
from src.back.tests.l02_services.turns.tactical.conftest import place_squad_on_grid


class TestTacticalMeleeService:
    def test_melee_attack_flank_angles(
        self, empty_battle_state, archetype_human_sword, weapon_sword
    ):
        sq_atk = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_sword)
        sq_atk.id = "atk"
        sq_def = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_sword)
        sq_def.id = "def"
        squads = {"atk": sq_atk, "def": sq_def}

        empty_battle_state.attacker_squad_ids = ["atk"]  # Атакующий смотрит вправо (+1)
        empty_battle_state.defender_squad_ids = ["def"]  # Защитник смотрит влево (-1)

        place_squad_on_grid(empty_battle_state, "atk", 1, 0)
        place_squad_on_grid(empty_battle_state, "def", 2, 0)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="atk", target_cell=CellCoordinates(x=2, y=0))
        )

        service = TacticalMeleeService()
        reports = service.resolve_melee_clashes(empty_battle_state, squads)

        assert len(reports) == 1
        assert (
            reports[0].flank_angle == "front"
        )  # Атака 2-1 = 1. Направление защитника -1. Лобовая.

    def test_melee_attack_rear_angle_causes_morale_shock(
        self, empty_battle_state, archetype_human_sword, weapon_sword
    ):
        sq_atk = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_sword)
        sq_atk.id = "atk"
        sq_def = Squad.create_new(archetype=archetype_human_sword)
        sq_def.id = "def"
        squads = {"atk": sq_atk, "def": sq_def}

        empty_battle_state.attacker_squad_ids = ["atk"]
        empty_battle_state.defender_squad_ids = ["def"]  # Защитник смотрит влево (-1)

        # Атакующий зашел в спину (справа от защитника)
        place_squad_on_grid(empty_battle_state, "def", 2, 0)
        place_squad_on_grid(empty_battle_state, "atk", 3, 0)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="atk", target_cell=CellCoordinates(x=2, y=0))
        )

        service = TacticalMeleeService()
        reports = service.resolve_melee_clashes(empty_battle_state, squads)

        assert len(reports) == 1
        assert reports[0].flank_angle == "rear"  # 2 - 3 = -1 == -1. Тыл.
        assert sq_def.state.morale < 50.0  # Штраф за спину
