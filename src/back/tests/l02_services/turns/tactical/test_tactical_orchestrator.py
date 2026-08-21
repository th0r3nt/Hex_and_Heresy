"""
Интеграционные тесты мастер-конвейера тактического боя.
"""

import pytest

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.constants import UnitSizeCategory
from src.back.l01_domain.combat.constants import BattlePhase
from src.back.l01_domain.combat.constants import CORPSE_PILE_UNIT_THRESHOLD
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.combat.models.state import SquadOrder
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.tests.l02_services.turns.tactical.conftest import place_squad_on_grid
from src.back.l02_services.turns.tactical.orchestrator import TacticalTurnOrchestrator
from src.back.l02_services.turns.tactical.combat.facade import TacticalCombatService
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


class TestTacticalOrchestratorFriendlyFireDeathAccounting:
    @pytest.mark.asyncio
    async def test_intercepted_shot_does_not_phantom_kill_original_target(
        self, empty_battle_state, archetype_human_sword, weapon_bow, fake_bus
    ):
        """
        Баг: при перехвате выстрела союзником убитые (rr.kills) начислялись
        и перехватчику (friendly_fire_squad_id), и изначальной цели
        (target_squad_id) — хотя урон домен применял только к перехватчику.
        """
        sq_archer = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_bow)
        sq_archer.id = "archers"
        sq_ally = Squad.create_new(archetype=archetype_human_sword)
        sq_ally.id = "ally_shield"
        sq_target = Squad.create_new(archetype=archetype_human_sword)
        sq_target.id = "enemy_target"

        squads = {"archers": sq_archer, "ally_shield": sq_ally, "enemy_target": sq_target}

        empty_battle_state.attacker_squad_ids = ["archers", "ally_shield"]
        empty_battle_state.defender_squad_ids = ["enemy_target"]

        place_squad_on_grid(empty_battle_state, "archers", 0, 0)
        place_squad_on_grid(empty_battle_state, "ally_shield", 2, 0)  # на линии огня
        place_squad_on_grid(empty_battle_state, "enemy_target", 4, 0)

        # pace=0.0, чтобы фаза перемещения не двигала лучников —
        # проверяем именно учёт смертей от выстрела, а не геометрию марша
        empty_battle_state.queue_order(
            SquadOrder(squad_id="archers", target_cell=CellCoordinates(x=4, y=0), pace=0.0)
        )

        orchestrator = TacticalTurnOrchestrator(event_bus=fake_bus)
        await orchestrator.execute_turn(
            battle_state=empty_battle_state,
            squads=squads,
            strategic_hex=HexCoordinates.from_axial(0, 0),
        )

        # Реальный урон (домен) получил только перехватчик
        assert sq_ally.state.unit_count < 100
        assert sq_target.state.unit_count == 100

        # Отчёт по потерям не должен приписывать смерти нетронутой цели
        assert empty_battle_state.accumulated_deaths_by_squad.get("enemy_target", 0) == 0
        assert empty_battle_state.accumulated_deaths_by_squad.get("ally_shield", 0) > 0


class TestTacticalOrchestratorCorpsePileAccumulatorReset:
    @pytest.mark.asyncio
    async def test_orchestrator_resets_accumulator_at_start_of_new_battle(
        self, empty_battle_state, archetype_human_sword, fake_bus
    ):
        """
        Баг: TacticalMoraleEnvironmentService._accumulated_corpse_weights —
        состояние экземпляра, переживающее execute_turn(). Если один и тот
        же combat_service обслуживает несколько разных боёв подряд, остаток
        веса трупов из прошлого боя на той же координате утекал в новый.
        """
        combat_service = TacticalCombatService()
        # имитируем "хвост" от уже завершённого боя: вес на клетке (5,5)
        # сам по себе ниже порога, но не должен доживать до следующего боя
        combat_service._morale_service._accumulated_corpse_weights[(5, 5)] = (
            CORPSE_PILE_UNIT_THRESHOLD - 1
        )

        orchestrator = TacticalTurnOrchestrator(
            combat_service=combat_service, event_bus=fake_bus
        )

        squad = Squad.create_new(archetype=archetype_human_sword)
        squad.id = "sq_1"
        squads = {"sq_1": squad}
        place_squad_on_grid(empty_battle_state, "sq_1", 5, 5)

        assert empty_battle_state.current_tick == 0  # новый бой

        await orchestrator.execute_turn(
            battle_state=empty_battle_state,
            squads=squads,
            strategic_hex=HexCoordinates.from_axial(0, 0),
        )

        weights = combat_service._morale_service._accumulated_corpse_weights
        assert weights.get((5, 5), 0.0) == 0.0

    @pytest.mark.asyncio
    async def test_accumulator_persists_across_ticks_within_same_battle(
        self, empty_battle_state, archetype_human_sword, fake_bus
    ):
        """Санити-чек: фикс не должен ломать накопление трупов внутри одного боя."""
        combat_service = TacticalCombatService()
        orchestrator = TacticalTurnOrchestrator(
            combat_service=combat_service, event_bus=fake_bus
        )

        squad = Squad.create_new(archetype=archetype_human_sword)
        squad.id = "sq_1"
        squads = {"sq_1": squad}
        place_squad_on_grid(empty_battle_state, "sq_1", 3, 3)

        # такт 1: current_tick был 0 -> сброс сработает (это ожидаемо для 1-го такта)
        await orchestrator.execute_turn(
            battle_state=empty_battle_state,
            squads=squads,
            strategic_hex=HexCoordinates.from_axial(0, 0),
        )
        combat_service._morale_service._accumulated_corpse_weights[(3, 3)] = 50.0

        # такт 2 на ТОМ ЖЕ battle_state: current_tick теперь 1, не 0 -> сброса быть не должно
        await orchestrator.execute_turn(
            battle_state=empty_battle_state,
            squads=squads,
            strategic_hex=HexCoordinates.from_axial(0, 0),
        )

        weights = combat_service._morale_service._accumulated_corpse_weights
        assert weights.get((3, 3)) == 50.0


class TestTacticalOrchestratorWeightedVeterancyKills:
    @pytest.mark.asyncio
    async def test_killing_huge_target_grants_eightfold_veterancy_weight(
        self, empty_battle_state, archetype_human_sword, weapon_sword, fake_bus
    ):
        """
        Убийство HUGE-цели должно давать вес x8 за юнита в накопителе
        ветеранства, а не x1, как было бы при использовании сырого
        kills_by_squad напрямую.
        """
        huge_stats = archetype_human_sword.base_stats.model_copy(
            update={"size_category": UnitSizeCategory.HUGE}
        )
        huge_archetype = archetype_human_sword.model_copy(update={"base_stats": huge_stats})

        sq_atk = Squad.create_new(archetype=archetype_human_sword, weapon=weapon_sword)
        sq_atk.id = "atk"
        sq_def = Squad.create_new(archetype=huge_archetype, custom_unit_count=1)
        sq_def.id = "def_huge"
        sq_def.state.hp_first_unit = 1.0  # гарантированная смерть от одного удара

        squads = {"atk": sq_atk, "def_huge": sq_def}
        empty_battle_state.attacker_squad_ids = ["atk"]
        empty_battle_state.defender_squad_ids = ["def_huge"]

        from src.back.tests.l02_services.turns.tactical.conftest import place_squad_on_grid
        from src.back.l01_domain.combat.models.state import SquadOrder
        from src.back.l01_domain.maps.models.tactical import CellCoordinates

        place_squad_on_grid(empty_battle_state, "atk", 1, 1)
        place_squad_on_grid(empty_battle_state, "def_huge", 2, 1)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="atk", target_cell=CellCoordinates(x=2, y=1))
        )

        orchestrator = TacticalTurnOrchestrator(event_bus=fake_bus)
        report = await orchestrator.execute_turn(
            battle_state=empty_battle_state,
            squads=squads,
            strategic_hex=HexCoordinates.from_axial(0, 0),
        )

        assert len(report.melee_reports) == 1
        assert report.melee_reports[0].kills == 1  # сырых убийств ровно одно

        # взвешенный вклад: 1 юнит * VETERANCY_KILL_WEIGHT_BY_SIZE[HUGE] (8.0)
        assert sq_atk.veterancy.accumulated_kill_weight == 8.0
