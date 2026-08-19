"""
Тесты стрельбы, линии видимости и погодных штрафов.
"""

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import TerrainType
from src.back.l01_domain.combat.models.state import SquadOrder
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l02_services.turns.tactical.combat.ranged import TacticalRangedService
from src.back.tests.l02_services.turns.tactical.conftest import place_squad_on_grid


class TestTacticalRangedService:
    def test_ranged_attack_inflicts_damage(
        self, empty_battle_state, archetype_human_sword, weapon_bow
    ):
        sq_archer = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_bow)
        sq_archer.id = "archers"
        sq_target = Squad.create_new(archetype=archetype_human_sword)
        sq_target.id = "target"
        squads = {"archers": sq_archer, "target": sq_target}

        place_squad_on_grid(empty_battle_state, "archers", 0, 0)
        place_squad_on_grid(empty_battle_state, "target", 4, 0)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="archers", target_cell=CellCoordinates(x=4, y=0))
        )

        service = TacticalRangedService()
        reports = service.resolve_ranged_attacks(empty_battle_state, squads)

        assert len(reports) == 1
        assert reports[0].kills > 0
        assert sq_target.state.unit_count < 100

    def test_obstacle_blocks_line_of_sight(
        self, empty_battle_state, archetype_human_sword, weapon_bow
    ):
        sq_archer = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_bow)
        sq_archer.id = "archers"
        sq_target = Squad.create_new(archetype=archetype_human_sword)
        sq_target.id = "target"
        squads = {"archers": sq_archer, "target": sq_target}

        place_squad_on_grid(empty_battle_state, "archers", 0, 0)
        place_squad_on_grid(empty_battle_state, "target", 4, 0)

        # Препятствие между ними
        for cell in empty_battle_state.cells:
            if cell.coordinates.to_tuple() == (2, 0):
                cell.terrain_type = TerrainType.MOUNTAIN

        empty_battle_state.queue_order(
            SquadOrder(squad_id="archers", target_cell=CellCoordinates(x=4, y=0))
        )

        service = TacticalRangedService()
        reports = service.resolve_ranged_attacks(empty_battle_state, squads)

        assert len(reports) == 0  # Залпа не было

    def test_friendly_fire(self, empty_battle_state, archetype_human_sword, weapon_bow):
        sq_archer = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_bow)
        sq_archer.id = "archers"
        sq_ally = Squad.create_new(archetype=archetype_human_sword)
        sq_ally.id = "ally"
        sq_target = Squad.create_new(archetype=archetype_human_sword)
        sq_target.id = "target"

        squads = {"archers": sq_archer, "ally": sq_ally, "target": sq_target}

        place_squad_on_grid(empty_battle_state, "archers", 0, 0)
        place_squad_on_grid(empty_battle_state, "ally", 2, 0)  # Союзник на линии огня
        place_squad_on_grid(empty_battle_state, "target", 4, 0)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="archers", target_cell=CellCoordinates(x=4, y=0))
        )

        service = TacticalRangedService()
        reports = service.resolve_ranged_attacks(empty_battle_state, squads)

        assert len(reports) == 1
        assert reports[0].friendly_fire_squad_id == "ally"
        assert sq_ally.state.unit_count < 100  # Союзник принял урон
