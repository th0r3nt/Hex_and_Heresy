"""
Тесты расчета перемещений, коллизий и расхода выносливости.
"""

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import (
    SPEED_MARCH_PACE,
    TerrainType,
)
from src.back.l01_domain.combat.models.effects import TerrainProfile
from src.back.l01_domain.combat.models.state import SquadOrder
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l02_services.turns.tactical.movement import TacticalMovementService
from src.back.tests.l02_services.turns.tactical.conftest import place_squad_on_grid


class TestTacticalMovementService:
    def test_march_movement_reaches_target(self, empty_battle_state, archetype_human_sword):
        fast_stats = archetype_human_sword.base_stats.model_copy(update={"base_speed": 3.0})
        fast_archetype = archetype_human_sword.model_copy(update={"base_stats": fast_stats})
        squad = Squad.create_new(archetype=fast_archetype)
        squad.id = "sq_1"
        squads = {squad.id: squad}

        place_squad_on_grid(empty_battle_state, "sq_1", 0, 0)

        target = CellCoordinates(x=3, y=0)
        empty_battle_state.queue_order(
            SquadOrder(squad_id="sq_1", target_cell=target, pace=SPEED_MARCH_PACE)
        )

        service = TacticalMovementService()
        reports = service.process_movement(empty_battle_state, squads, ["sq_1"])

        assert len(reports) == 1
        assert reports[0].end_cell == target
        assert not reports[0].was_blocked

    def test_blocked_by_other_unit(self, empty_battle_state, archetype_human_sword):
        sq1 = Squad.create_new(archetype=archetype_human_sword)
        sq1.id = "sq_1"
        sq2 = Squad.create_new(archetype=archetype_human_sword)
        sq2.id = "sq_2"
        squads = {"sq_1": sq1, "sq_2": sq2}

        place_squad_on_grid(empty_battle_state, "sq_1", 0, 0)
        place_squad_on_grid(empty_battle_state, "sq_2", 2, 0)  # Блокирует путь

        target = CellCoordinates(x=4, y=0)
        empty_battle_state.queue_order(
            SquadOrder(squad_id="sq_1", target_cell=target, pace=SPEED_MARCH_PACE)
        )

        service = TacticalMovementService()
        reports = service.process_movement(empty_battle_state, squads, ["sq_1"])

        assert reports[0].end_cell == CellCoordinates(x=1, y=0)
        assert reports[0].was_blocked is True

    def test_impassable_terrain_blocks_movement(
        self, empty_battle_state, archetype_human_sword
    ):
        squad = Squad.create_new(archetype=archetype_human_sword)
        squad.id = "sq_1"
        squads = {"sq_1": squad}

        place_squad_on_grid(empty_battle_state, "sq_1", 0, 0)

        # Делаем клетку (1, 0) горой
        for cell in empty_battle_state.cells:
            if cell.coordinates.to_tuple() == (1, 0):
                cell.terrain_type = TerrainType.MOUNTAIN
                break

        target = CellCoordinates(x=3, y=0)
        empty_battle_state.queue_order(
            SquadOrder(squad_id="sq_1", target_cell=target, pace=SPEED_MARCH_PACE)
        )

        profiles = {
            TerrainType.MOUNTAIN: TerrainProfile(
                terrain_type=TerrainType.MOUNTAIN, movement_speed_modifier=0.0
            )
        }
        service = TacticalMovementService()
        reports = service.process_movement(
            empty_battle_state, squads, ["sq_1"], terrain_profiles=profiles
        )

        assert reports[0].end_cell == CellCoordinates(x=0, y=0)
        assert reports[0].was_blocked is True

    def test_fleeing_squad_runs_to_border(self, empty_battle_state, archetype_human_sword):
        squad = Squad.create_new(archetype=archetype_human_sword)
        squad.id = "sq_flee"
        squad.state.is_in_panic = True  # Триггер бегства
        squads = {"sq_flee": squad}

        # Атакующие бегут налево (к x=0)
        empty_battle_state.attacker_squad_ids = ["sq_flee"]
        place_squad_on_grid(empty_battle_state, "sq_flee", 5, 5)

        service = TacticalMovementService()
        reports = service.process_movement(empty_battle_state, squads, ["sq_flee"])

        assert reports[0].is_fleeing is True
        assert reports[0].end_cell.x < 5  # Убежал влево
