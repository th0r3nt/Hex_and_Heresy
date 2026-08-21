"""
Тесты расчета направлений взгляда отрядов (Facing), углов атак
(лоб, фланг, тыл), бронепробития и морального шока от удара в спину.
"""

import pytest

from src.back.l01_domain.army.constants import (
    ArmorCategory,
    EquipmentSlot,
    EquipmentTag,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import FacingAngle
from src.back.l01_domain.combat.models.state import SquadOrder
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l02_services.turns.tactical.combat.melee import TacticalMeleeService
from src.back.tests.l02_services.turns.tactical.conftest import place_squad_on_grid


@pytest.fixture
def heavy_plate() -> Equipment:
    return Equipment(
        id="armor_heavy_plate",
        name="Тяжелые латы",
        lore="...",
        slot=EquipmentSlot.ARMOR,
        category=ArmorCategory.PLATE,
        tags={EquipmentTag.HEAVY},
        tier=3,
        stats=EquipmentStats(armor_bonus=10.0),
    )


@pytest.fixture
def polearm_spear() -> Equipment:
    return Equipment(
        id="wpn_spear_2h",
        name="Длинная пика",
        lore="...",
        slot=EquipmentSlot.WEAPON,
        category=WeaponCategory.SPEAR,
        tags={EquipmentTag.TWO_HANDED, EquipmentTag.BRACEABLE},
        tier=1,
        stats=EquipmentStats(damage=8.0, range_hexes=2),
    )


class TestMeleeFlankingAndFacingGeometry:
    def test_frontal_attack_uses_standard_armor_and_no_morale_shock(
        self, empty_battle_state, archetype_human_sword, heavy_plate, weapon_sword
    ):
        sq_atk = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_sword)
        sq_atk.id = "attacker"
        sq_def = Squad.create_new(archetype=archetype_human_sword, armor=heavy_plate)
        sq_def.id = "defender"
        squads = {"attacker": sq_atk, "defender": sq_def}

        # Атакующий слева на (1, 1), защитник справа на (2, 1)
        # Атакующий смотрит вправо (+1), защитник смотрит влево (-1)
        empty_battle_state.attacker_squad_ids = ["attacker"]
        empty_battle_state.defender_squad_ids = ["defender"]
        place_squad_on_grid(empty_battle_state, "attacker", 1, 1)
        place_squad_on_grid(empty_battle_state, "defender", 2, 1)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="attacker", target_cell=CellCoordinates(x=2, y=1))
        )

        service = TacticalMeleeService()
        reports = service.resolve_melee_clashes(empty_battle_state, squads)

        assert len(reports) == 1
        report = reports[0]
        assert report.flank_angle == FacingAngle.FRONT
        # Мораль защитника осталась нетронутой шоком спины
        assert sq_def.state.morale == 50.0

    def test_flank_attack_ignores_half_armor_and_causes_light_shock(
        self, empty_battle_state, archetype_human_sword, heavy_plate, weapon_sword
    ):
        sq_atk = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_sword)
        sq_atk.id = "attacker"
        sq_def = Squad.create_new(archetype=archetype_human_sword, armor=heavy_plate)
        sq_def.id = "defender"
        squads = {"attacker": sq_atk, "defender": sq_def}

        # Атакующий сверху на (2, 0), защитник снизу на (2, 1)
        # dx == 0 -> боковой удар (во фланг)
        empty_battle_state.attacker_squad_ids = ["attacker"]
        empty_battle_state.defender_squad_ids = ["defender"]
        place_squad_on_grid(empty_battle_state, "attacker", 2, 0)
        place_squad_on_grid(empty_battle_state, "defender", 2, 1)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="attacker", target_cell=CellCoordinates(x=2, y=1))
        )

        service = TacticalMeleeService()
        reports = service.resolve_melee_clashes(empty_battle_state, squads)

        assert len(reports) == 1
        report = reports[0]
        assert report.flank_angle == FacingAngle.FLANK
        # Моральный шок за фланг: 50.0 - 5.0 = 45.0
        assert sq_def.state.morale == 45.0

    def test_rear_attack_ignores_full_armor_and_causes_heavy_shock(
        self, empty_battle_state, archetype_human_sword, heavy_plate, weapon_sword
    ):
        sq_atk = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_sword)
        sq_atk.id = "attacker"
        sq_def = Squad.create_new(archetype=archetype_human_sword, armor=heavy_plate)
        sq_def.id = "defender"
        squads = {"attacker": sq_atk, "defender": sq_def}

        # Защитник смотрит влево (-1), стоит на (2, 1).
        # Атакующий зашел в спину справа на (3, 1). dx = 2 - 3 = -1 == facing_dx -> Тыл
        empty_battle_state.attacker_squad_ids = ["attacker"]
        empty_battle_state.defender_squad_ids = ["defender"]
        place_squad_on_grid(empty_battle_state, "defender", 2, 1)
        place_squad_on_grid(empty_battle_state, "attacker", 3, 1)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="attacker", target_cell=CellCoordinates(x=2, y=1))
        )

        service = TacticalMeleeService()
        reports = service.resolve_melee_clashes(empty_battle_state, squads)

        assert len(reports) == 1
        report = reports[0]
        assert report.flank_angle == FacingAngle.REAR
        # Моральный шок за тыл: 50.0 - 15.0 = 35.0
        assert sq_def.state.morale == 35.0

    def test_polearm_long_range_melee_strike(
        self, empty_battle_state, archetype_human_sword, polearm_spear
    ):
        sq_spear = Squad.create_new(archetype=archetype_human_sword, weapon=polearm_spear)
        sq_spear.id = "spearmen"
        sq_enemy = Squad.create_new(archetype=archetype_human_sword)
        sq_enemy.id = "enemy"
        squads = {"spearmen": sq_spear, "enemy": sq_enemy}

        empty_battle_state.attacker_squad_ids = ["spearmen"]
        empty_battle_state.defender_squad_ids = ["enemy"]

        # Дистанция ровно 2 клетки (через клетку)
        place_squad_on_grid(empty_battle_state, "spearmen", 1, 1)
        place_squad_on_grid(empty_battle_state, "enemy", 3, 1)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="spearmen", target_cell=CellCoordinates(x=3, y=1))
        )

        service = TacticalMeleeService()
        reports = service.resolve_melee_clashes(empty_battle_state, squads)

        assert len(reports) == 1
        assert reports[0].kills > 0
