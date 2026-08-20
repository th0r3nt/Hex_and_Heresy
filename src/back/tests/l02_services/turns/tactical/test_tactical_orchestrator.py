"""
Интеграционные тесты мастер-конвейера тактического боя.
"""

import pytest

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import BattlePhase
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l02_services.turns.tactical.orchestrator import TacticalTurnOrchestrator
from src.back.utils.event.registry import GameEvents


class TestTacticalTurnOrchestrator:
    @pytest.mark.asyncio
    async def test_full_tactical_turn_pipeline(
        self, empty_battle_state, archetype_human_sword, weapon_sword, fake_bus
    ):
        # Подготовка
        sq_atk = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_sword)
        sq_atk.id = "atk"
        sq_def = Squad.create_new(archetype=archetype_human_sword)
        sq_def.id = "def"
        # Защитник почти мертв
        sq_def.state.unit_count = 1
        sq_def.state.hp_first_unit = 1.0

        squads = {"atk": sq_atk, "def": sq_def}
        empty_battle_state.attacker_squad_ids = ["atk"]
        empty_battle_state.defender_squad_ids = ["def"]
        empty_battle_state.current_tick = 0

        # Ставим рядом, чтобы в рукопашной добили
        from src.back.tests.l02_services.turns.tactical.conftest import place_squad_on_grid

        place_squad_on_grid(empty_battle_state, "atk", 1, 1)
        place_squad_on_grid(empty_battle_state, "def", 2, 1)

        from src.back.l01_domain.combat.models.state import SquadOrder
        from src.back.l01_domain.maps.models.tactical import CellCoordinates

        empty_battle_state.queue_order(
            SquadOrder(squad_id="atk", target_cell=CellCoordinates(x=2, y=1))
        )

        orchestrator = TacticalTurnOrchestrator(event_bus=fake_bus)

        # Запуск конвейера
        report = await orchestrator.execute_turn(
            battle_state=empty_battle_state,
            squads=squads,
            strategic_hex=HexCoordinates.from_axial(0, 0),
        )

        # Проверки отчета
        assert report.tick == 1
        assert report.phase == BattlePhase.AFTERMATH
        assert len(report.melee_reports) == 1
        assert report.melee_reports[0].kills == 1

        # Проверка завершения боя (защитник уничтожен)
        assert report.is_battle_finished is True
        assert report.victor_faction_id == "humans"

        # Проверка создания лута
        assert report.loot_site is not None
        assert len(report.loot_site.corpses) > 0

        # Проверка публикации событий
        event_names = [name for name, _ in fake_bus.events]
        assert GameEvents.Tactical.TURN_STARTED in event_names
        assert GameEvents.Tactical.BATTLE_COMPLETED in event_names
