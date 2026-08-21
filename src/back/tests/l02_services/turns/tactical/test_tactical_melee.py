"""
Тесты рукопашного боя, флангов и тылов.
"""

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import FacingAngle
from src.back.l01_domain.combat.models.state import SquadOrder
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l01_domain.army.constants import EquipmentSlot, EquipmentTag, WeaponCategory
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
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
            reports[0].flank_angle == FacingAngle.FRONT
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
        assert reports[0].flank_angle == FacingAngle.REAR  # 2 - 3 = -1 == -1. Тыл.
        assert sq_def.state.morale < 50.0  # Штраф за спину


class TestTacticalMeleeWeaponRangeValidation:
    def test_short_weapon_cannot_strike_at_distance_two(
        self, empty_battle_state, archetype_human_sword, weapon_sword
    ):
        """
        Баг: melee.py игнорировал range_hexes оружия и пускал одноручный
        меч (range=1) в бой на дистанции 2 клетки.
        """
        sq_atk = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_sword)
        sq_atk.id = "atk"
        sq_def = Squad.create_new(archetype=archetype_human_sword)
        sq_def.id = "def"
        squads = {"atk": sq_atk, "def": sq_def}

        empty_battle_state.attacker_squad_ids = ["atk"]
        empty_battle_state.defender_squad_ids = ["def"]

        place_squad_on_grid(empty_battle_state, "atk", 0, 0)
        place_squad_on_grid(empty_battle_state, "def", 2, 0)  # дистанция 2

        empty_battle_state.queue_order(
            SquadOrder(squad_id="atk", target_cell=CellCoordinates(x=2, y=0))
        )

        service = TacticalMeleeService()
        reports = service.resolve_melee_clashes(empty_battle_state, squads)

        assert reports == []
        assert sq_def.state.unit_count == 100

    def test_polearm_with_range_two_still_strikes_at_distance_two(
        self, empty_battle_state, archetype_human_sword
    ):
        """Санити-чек: легитимное оружие с range=2 (алебарда) фикс не ломает."""
        polearm = Equipment(
            id="wpn_test_polearm",
            name="Тестовая алебарда",
            lore="...",
            slot=EquipmentSlot.WEAPON,
            category=WeaponCategory.POLEARM,
            tags={EquipmentTag.TWO_HANDED, EquipmentTag.BRACEABLE},
            tier=1,
            stats=EquipmentStats(damage=6.0, range_hexes=2),
        )
        sq_atk = Squad.create_new(archetype=archetype_human_sword, weapon=polearm)
        sq_atk.id = "atk"
        sq_def = Squad.create_new(archetype=archetype_human_sword)
        sq_def.id = "def"
        squads = {"atk": sq_atk, "def": sq_def}

        empty_battle_state.attacker_squad_ids = ["atk"]
        empty_battle_state.defender_squad_ids = ["def"]

        place_squad_on_grid(empty_battle_state, "atk", 0, 0)
        place_squad_on_grid(empty_battle_state, "def", 2, 0)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="atk", target_cell=CellCoordinates(x=2, y=0))
        )

        service = TacticalMeleeService()
        reports = service.resolve_melee_clashes(empty_battle_state, squads)

        assert len(reports) == 1
        assert reports[0].kills > 0

    def test_ranged_weapon_is_never_resolved_by_melee_service(
        self, empty_battle_state, archetype_human_sword, weapon_bow
    ):
        """
        Баг-следствие: лучник на дистанции 2 получал урон дважды — через
        ranged.py и через melee.py (тот не смотрел на range_hexes вообще).
        """
        sq_atk = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_bow)
        sq_atk.id = "atk"
        sq_def = Squad.create_new(archetype=archetype_human_sword)
        sq_def.id = "def"
        squads = {"atk": sq_atk, "def": sq_def}

        empty_battle_state.attacker_squad_ids = ["atk"]
        empty_battle_state.defender_squad_ids = ["def"]

        place_squad_on_grid(empty_battle_state, "atk", 0, 0)
        place_squad_on_grid(empty_battle_state, "def", 2, 0)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="atk", target_cell=CellCoordinates(x=2, y=0))
        )

        service = TacticalMeleeService()
        reports = service.resolve_melee_clashes(empty_battle_state, squads)

        assert reports == []
