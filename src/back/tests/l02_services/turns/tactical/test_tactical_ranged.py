"""
Тесты стрельбы, линии видимости и погодных штрафов.
"""

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import (
    NIGHT_VISION_RANGE_CELLS,
    TerrainType,
    TimeOfDay,
    WeatherCondition,
)
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

    def test_firearm_with_blackpowder_tag_misfires_in_rain(
        self, empty_battle_state, archetype_human_sword, weapon_arquebus
    ):
        sq_gunner = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_arquebus)
        sq_gunner.id = "gunners"
        sq_target = Squad.create_new(archetype=archetype_human_sword)
        sq_target.id = "target"
        squads = {"gunners": sq_gunner, "target": sq_target}

        empty_battle_state.weather = WeatherCondition.HEAVY_RAIN
        place_squad_on_grid(empty_battle_state, "gunners", 0, 0)
        place_squad_on_grid(empty_battle_state, "target", 4, 0)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="gunners", target_cell=CellCoordinates(x=4, y=0))
        )

        service = TacticalRangedService()
        reports = service.resolve_ranged_attacks(empty_battle_state, squads)

        assert len(reports) == 1
        assert reports[0].is_misfire is True
        assert reports[0].kills == 0
        assert sq_target.state.unit_count == 100

class TestRangedVisibilityLimits:
    """
    Туман войны на тактической сетке: дальность оружия ничего не значит,
    если цель не видно (см. combat/visibility.py).
    """

    @staticmethod
    def _archers_and_target(battle_state, archetype, weapon, target_x: int):
        """Ставит лучников в начало ряда, а мишень - на заданной дистанции."""
        archers = Squad.create_new(archetype=archetype, weapon=weapon)
        archers.id = "archers"
        target = Squad.create_new(archetype=archetype)
        target.id = "target"

        place_squad_on_grid(battle_state, "archers", 0, 0)
        place_squad_on_grid(battle_state, "target", target_x, 0)
        battle_state.queue_order(
            SquadOrder(squad_id="archers", target_cell=CellCoordinates(x=target_x, y=0))
        )

        return {"archers": archers, "target": target}, target

    def test_night_forbids_shots_beyond_three_cells(
        self, empty_battle_state, archetype_human_sword, weapon_bow
    ):
        """
        Ночью лук бьет на шесть клеток, а видно на три: залпа по дальней
        цели не будет.
        """
        squads, target = self._archers_and_target(
            empty_battle_state, archetype_human_sword, weapon_bow, target_x=5
        )
        empty_battle_state.time_of_day = TimeOfDay.NEON_HOURS

        reports = TacticalRangedService().resolve_ranged_attacks(
            empty_battle_state, squads
        )

        assert len(reports) == 1
        assert reports[0].is_out_of_sight is True
        assert reports[0].kills == 0
        assert target.state.unit_count == 100

    def test_night_still_allows_shots_inside_the_lit_circle(
        self, empty_battle_state, archetype_human_sword, weapon_bow
    ):
        """Цель на границе ночного обзора остается под обстрелом."""
        squads, target = self._archers_and_target(
            empty_battle_state,
            archetype_human_sword,
            weapon_bow,
            target_x=NIGHT_VISION_RANGE_CELLS,
        )
        empty_battle_state.time_of_day = TimeOfDay.NEON_HOURS

        reports = TacticalRangedService().resolve_ranged_attacks(
            empty_battle_state, squads
        )

        assert len(reports) == 1
        assert reports[0].is_out_of_sight is False
        assert reports[0].kills > 0
        assert target.state.unit_count < 100

    def test_clear_grey_hours_do_not_limit_the_bow(
        self, empty_battle_state, archetype_human_sword, weapon_bow
    ):
        """Днем при ясном небе поле просматривается на всю дальность оружия."""
        squads, target = self._archers_and_target(
            empty_battle_state, archetype_human_sword, weapon_bow, target_x=6
        )

        reports = TacticalRangedService().resolve_ranged_attacks(
            empty_battle_state, squads
        )

        assert reports[0].is_out_of_sight is False
        assert target.state.unit_count < 100

    def test_ash_storm_at_night_leaves_only_the_next_cell(
        self, empty_battle_state, archetype_human_sword, weapon_arquebus
    ):
        """
        Пепельная буря в неоновые часы забирает весь ночной запас: аркебузир
        не различает цель уже в двух клетках.
        """
        squads, target = self._archers_and_target(
            empty_battle_state, archetype_human_sword, weapon_arquebus, target_x=2
        )
        empty_battle_state.time_of_day = TimeOfDay.NEON_HOURS
        empty_battle_state.weather = WeatherCondition.ASH_STORM

        reports = TacticalRangedService().resolve_ranged_attacks(
            empty_battle_state, squads
        )

        assert reports[0].is_out_of_sight is True
        assert target.state.unit_count == 100
