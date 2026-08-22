"""
Тесты морали, паники, гор трупов и ветеранства.
"""

from src.back.l01_domain.army.constants import PANIC_THRESHOLD_MORALE
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import CORPSE_PILE_UNIT_THRESHOLD, TerrainType
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l02_services.turns.tactical.combat.morale import TacticalMoraleEnvironmentService
from src.back.tests.l02_services.turns.tactical.conftest import place_squad_on_grid


class TestTacticalMoraleEnvironmentService:
    def test_chain_panic_triggers_on_neighbors(
        self, empty_battle_state, archetype_human_sword
    ):
        sq1 = Squad.create_new(archetype=archetype_human_sword)
        sq1.id = "sq_1"
        sq1.state.morale = PANIC_THRESHOLD_MORALE
        sq2 = Squad.create_new(archetype=archetype_human_sword)
        sq2.id = "sq_2"
        squads = {"sq_1": sq1, "sq_2": sq2}

        empty_battle_state.attacker_squad_ids = ["sq_1", "sq_2"]
        place_squad_on_grid(empty_battle_state, "sq_1", 1, 1)
        place_squad_on_grid(empty_battle_state, "sq_2", 1, 2)

        service = TacticalMoraleEnvironmentService()
        report = service.process_morale_and_environment(
            empty_battle_state,
            squads,
            all_deaths_by_squad={"sq_1": 10},
            all_kills_by_squad={},
            all_weighted_kills_by_squad={},
        )

        assert "sq_1" in report.panicking_squad_ids
        assert "sq_2" in report.chain_panic_shocks
        assert sq2.state.morale < 50.0

    def test_corpse_pile_generation(self, empty_battle_state, archetype_human_sword):
        sq1 = Squad.create_new(archetype=archetype_human_sword)
        sq1.id = "sq_1"
        squads = {"sq_1": sq1}

        place_squad_on_grid(empty_battle_state, "sq_1", 2, 2)

        service = TacticalMoraleEnvironmentService()
        deaths = CORPSE_PILE_UNIT_THRESHOLD + 10
        report = service.process_morale_and_environment(
            empty_battle_state,
            squads,
            all_deaths_by_squad={"sq_1": deaths},
            all_kills_by_squad={},
            all_weighted_kills_by_squad={},
        )

        assert len(report.new_corpse_piles) == 1
        cell = next(c for c in empty_battle_state.cells if c.coordinates.to_tuple() == (2, 2))
        assert cell.terrain_type == TerrainType.CORPSE_PILE


class TestTacticalVeterancyKillWeightAccumulation:
    def test_weighted_kills_below_threshold_do_not_trigger_candidacy(
        self, empty_battle_state, archetype_human_sword
    ):
        sq1 = Squad.create_new(archetype=archetype_human_sword)
        sq1.id = "sq_mvp"
        squads = {"sq_mvp": sq1}

        service = TacticalMoraleEnvironmentService()
        # 100 средних (MEDIUM) целей * вес 2.0 = 200.0 - ниже порога 500.0
        report = service.process_morale_and_environment(
            empty_battle_state,
            squads,
            all_deaths_by_squad={},
            all_kills_by_squad={},
            all_weighted_kills_by_squad={"sq_mvp": 200.0},
        )

        assert "sq_mvp" not in report.veterancy_candidate_ids
        assert sq1.veterancy.accumulated_kill_weight == 200.0

    def test_crossing_kill_weight_threshold_triggers_candidacy(
        self, empty_battle_state, archetype_human_sword
    ):
        sq1 = Squad.create_new(archetype=archetype_human_sword)
        sq1.id = "sq_mvp"
        squads = {"sq_mvp": sq1}

        service = TacticalMoraleEnvironmentService()
        report = service.process_morale_and_environment(
            empty_battle_state,
            squads,
            all_deaths_by_squad={},
            all_kills_by_squad={},
            all_weighted_kills_by_squad={"sq_mvp": 500.0},
        )

        assert "sq_mvp" in report.veterancy_candidate_ids

    def test_kill_weight_accumulates_across_separate_battle_calls(
        self, empty_battle_state, archetype_human_sword
    ):
        """
        Ядро задачи: счётчик должен переживать несколько отдельных боёв -
        симулируем это двумя независимыми вызовами на одном и том же
        объекте Squad с разными TacticalBattleState.
        """
        sq1 = Squad.create_new(archetype=archetype_human_sword)
        sq1.id = "sq_mvp"
        squads = {"sq_mvp": sq1}

        service = TacticalMoraleEnvironmentService()

        # "Бой 1": набрано 300.0 - ниже порога
        report_1 = service.process_morale_and_environment(
            empty_battle_state,
            squads,
            all_deaths_by_squad={},
            all_kills_by_squad={},
            all_weighted_kills_by_squad={"sq_mvp": 300.0},
        )
        assert "sq_mvp" not in report_1.veterancy_candidate_ids

        # "Бой 2" - новое состояние боя, тот же Squad: добираем ещё 300.0,
        # суммарно 600.0, порог пройден именно на этом вызове
        battle_state_2 = TacticalBattleState()
        report_2 = service.process_morale_and_environment(
            battle_state_2,
            squads,
            all_deaths_by_squad={},
            all_kills_by_squad={},
            all_weighted_kills_by_squad={"sq_mvp": 300.0},
        )
        assert "sq_mvp" in report_2.veterancy_candidate_ids
        assert sq1.veterancy.accumulated_kill_weight == 600.0

    def test_already_named_squad_is_never_a_candidate_again(
        self, empty_battle_state, archetype_human_sword
    ):
        sq1 = Squad.create_new(archetype=archetype_human_sword)
        sq1.id = "sq_veteran"
        sq1.veterancy.promote(
            commander_name="Маркус",
            squad_nickname="Грязные стрелки Маркуса",
            trait_name="Высокомерные",
            lore="...",
        )
        squads = {"sq_veteran": sq1}

        service = TacticalMoraleEnvironmentService()
        report = service.process_morale_and_environment(
            empty_battle_state,
            squads,
            all_deaths_by_squad={},
            all_kills_by_squad={},
            all_weighted_kills_by_squad={"sq_veteran": 9999.0},
        )

        assert "sq_veteran" not in report.veterancy_candidate_ids
