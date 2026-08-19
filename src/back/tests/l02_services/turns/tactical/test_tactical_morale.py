"""
Тесты морали, паники, гор трупов и ветеранства.
"""

from src.back.l01_domain.army.constants import PANIC_THRESHOLD_MORALE
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import CORPSE_PILE_UNIT_THRESHOLD, TerrainType
from src.back.l02_services.turns.tactical.combat.morale import TacticalMoraleEnvironmentService
from src.back.tests.l02_services.turns.tactical.conftest import place_squad_on_grid


class TestTacticalMoraleEnvironmentService:
    def test_chain_panic_triggers_on_neighbors(
        self, empty_battle_state, archetype_human_sword
    ):
        sq1 = Squad.create_new(archetype=archetype_human_sword)
        sq1.id = "sq_1"
        sq1.state.morale = PANIC_THRESHOLD_MORALE  # Упадет в панику
        sq2 = Squad.create_new(archetype=archetype_human_sword)
        sq2.id = "sq_2"  # Сосед
        squads = {"sq_1": sq1, "sq_2": sq2}

        empty_battle_state.attacker_squad_ids = ["sq_1", "sq_2"]
        place_squad_on_grid(empty_battle_state, "sq_1", 1, 1)
        place_squad_on_grid(empty_battle_state, "sq_2", 1, 2)

        service = TacticalMoraleEnvironmentService()
        report = service.process_morale_and_environment(
            empty_battle_state, squads, all_deaths_by_squad={"sq_1": 10}, all_kills_by_squad={}
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

        # Добавляем смертей больше порога
        deaths = CORPSE_PILE_UNIT_THRESHOLD + 10
        report = service.process_morale_and_environment(
            empty_battle_state,
            squads,
            all_deaths_by_squad={"sq_1": deaths},
            all_kills_by_squad={},
        )

        assert len(report.new_corpse_piles) == 1

        # Проверяем мутацию клетки
        cell = next(c for c in empty_battle_state.cells if c.coordinates.to_tuple() == (2, 2))
        assert cell.terrain_type == TerrainType.CORPSE_PILE

    def test_veterancy_candidate_triggered(self, empty_battle_state, archetype_human_sword):
        sq1 = Squad.create_new(archetype=archetype_human_sword)
        sq1.id = "sq_mvp"
        squads = {"sq_mvp": sq1}

        service = TacticalMoraleEnvironmentService()
        report = service.process_morale_and_environment(
            empty_battle_state,
            squads,
            all_deaths_by_squad={},
            all_kills_by_squad={"sq_mvp": 120},
        )

        assert "sq_mvp" in report.veterancy_candidate_ids
