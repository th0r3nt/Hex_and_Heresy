"""
Мастер-оркестратор тактического боя (WEGO конвейер).
"""

from typing import Optional

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.army.constants import VETERANCY_KILL_WEIGHT_BY_SIZE
from src.back.l01_domain.combat.constants import BattlePhase, TerrainType
from src.back.l01_domain.combat.models.effects import TerrainProfile
from src.back.l01_domain.combat.models.reports import TacticalTurnReport
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.constants import (
    DEFAULT_BATTLEFIELD_DECAY_TICKS,
    DEFAULT_EQUIPMENT_SALVAGE_RATIO,
)
from src.back.l01_domain.world.models.battleground import (
    BattlefieldCorpsePile,
    BattlefieldLootSite,
)
from src.back.l02_services.turns.tactical.combat.facade import TacticalCombatService
from src.back.l02_services.turns.tactical.initiative import TacticalInitiativeService
from src.back.l02_services.turns.tactical.movement import TacticalMovementService
from src.back.utils.event.registry import GameEvents


def _accumulate_weighted_kills(
    weighted_kills_by_squad: dict[str, float],
    squads: dict[str, Squad],
    killer_squad_id: str,
    victim_squad_id: Optional[str],
    victim_deaths: int,
) -> None:
    """
    Прибавляет вклад в счётчик ветеранства killer_squad_id, взвешенный по
    габариту жертвы (VETERANCY_KILL_WEIGHT_BY_SIZE). Отдельно от сырого
    kills_by_squad, который остаётся как есть для остальной статистики отчёта.
    """
    if victim_squad_id is None or victim_deaths <= 0:
        return

    victim_squad = squads.get(victim_squad_id)
    if victim_squad is None:
        return

    weight_per_unit = VETERANCY_KILL_WEIGHT_BY_SIZE.get(victim_squad.size_category, 1.0)
    weighted_kills_by_squad[killer_squad_id] = (
        weighted_kills_by_squad.get(killer_squad_id, 0.0) + weight_per_unit * victim_deaths
    )


class TacticalTurnOrchestrator:
    """
    Главный оркестратор тактического хода.

    Строго последовательно проводит раунд через 6 фаз WEGO-конвейера:
    [1. Инициатива] -> [2. Натиск] -> [3. Движение] -> [4. Бой] -> [5. Мораль и трупы] -> [6. Исход].
    """

    def __init__(
        self,
        initiative_service: Optional[TacticalInitiativeService] = None,
        movement_service: Optional[TacticalMovementService] = None,
        combat_service: Optional[TacticalCombatService] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._event_bus = event_bus
        self._initiative_service = initiative_service or TacticalInitiativeService()
        self._movement_service = movement_service or TacticalMovementService()
        self._combat_service = combat_service or TacticalCombatService()

    async def execute_turn(
        self,
        battle_state: TacticalBattleState,
        squads: dict[str, Squad],
        strategic_hex: HexCoordinates,
        commanders: Optional[dict[str, Commander]] = None,
        heroes: Optional[dict[str, Hero]] = None,
        terrain_profiles: Optional[dict[TerrainType, TerrainProfile]] = None,
    ) -> TacticalTurnReport:
        """
        Выполняет полный расчет одного тактического раунда (30 секунд).
        """

        deaths_by_squad: dict[str, int] = {}
        kills_by_squad: dict[str, int] = {}
        weighted_kills_by_squad: dict[str, float] = {}

        is_new_battle = battle_state.current_tick == 0
        battle_state.current_tick += 1
        battle_state.advance_phase(BattlePhase.RESOLUTION)

        if is_new_battle:
            self._combat_service.reset_battle_accumulators()

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Tactical.TURN_STARTED,
                battle_id=battle_state.id,
                tick=battle_state.current_tick,
            )

        deaths_by_squad: dict[str, int] = {}
        kills_by_squad: dict[str, int] = {}

        # 1. Расчет инициативы
        turn_order = self._initiative_service.get_turn_order(
            squads=squads,
            battle_state=battle_state,
            commanders=commanders,
            heroes=heroes,
        )

        # 2. Фаза натиска
        charge_reports = self._combat_service.resolve_charges(
            battle_state=battle_state,
            squads=squads,
            terrain_profiles=terrain_profiles,
        )

        for cr in charge_reports:
            deaths_by_squad[cr.attacker_squad_id] = (
                deaths_by_squad.get(cr.attacker_squad_id, 0) + cr.attacker_deaths
            )
            deaths_by_squad[cr.defender_squad_id] = (
                deaths_by_squad.get(cr.defender_squad_id, 0) + cr.defender_deaths
            )
            kills_by_squad[cr.attacker_squad_id] = (
                kills_by_squad.get(cr.attacker_squad_id, 0) + cr.defender_deaths
            )
            kills_by_squad[cr.defender_squad_id] = (
                kills_by_squad.get(cr.defender_squad_id, 0) + cr.attacker_deaths
            )

            _accumulate_weighted_kills(
                weighted_kills_by_squad,
                squads,
                cr.attacker_squad_id,
                cr.defender_squad_id,
                cr.defender_deaths,
            )
            _accumulate_weighted_kills(
                weighted_kills_by_squad,
                squads,
                cr.defender_squad_id,
                cr.attacker_squad_id,
                cr.attacker_deaths,
            )

        # 3. Пошаговое перемещение
        movement_reports = self._movement_service.process_movement(
            battle_state=battle_state,
            squads=squads,
            ordered_squad_ids=turn_order,
            terrain_profiles=terrain_profiles,
        )

        # 4. Дальний бой
        ranged_reports = self._combat_service.resolve_ranged_combat(
            battle_state=battle_state,
            squads=squads,
            terrain_profiles=terrain_profiles,
        )

        for rr in ranged_reports:
            if rr.friendly_fire_squad_id:
                deaths_by_squad[rr.friendly_fire_squad_id] = (
                    deaths_by_squad.get(rr.friendly_fire_squad_id, 0) + rr.friendly_fire_kills
                )
                _accumulate_weighted_kills(
                    weighted_kills_by_squad,
                    squads,
                    rr.attacker_squad_id,
                    rr.friendly_fire_squad_id,
                    rr.friendly_fire_kills,
                )
            elif rr.target_squad_id:
                deaths_by_squad[rr.target_squad_id] = (
                    deaths_by_squad.get(rr.target_squad_id, 0) + rr.kills
                )
                _accumulate_weighted_kills(
                    weighted_kills_by_squad,
                    squads,
                    rr.attacker_squad_id,
                    rr.target_squad_id,
                    rr.kills,
                )
            kills_by_squad[rr.attacker_squad_id] = (
                kills_by_squad.get(rr.attacker_squad_id, 0) + rr.kills
            )

        # 5. Ближний бой
        melee_reports = self._combat_service.resolve_melee_combat(
            battle_state=battle_state,
            squads=squads,
        )

        for mr in melee_reports:
            deaths_by_squad[mr.defender_squad_id] = (
                deaths_by_squad.get(mr.defender_squad_id, 0) + mr.kills
            )
            kills_by_squad[mr.attacker_squad_id] = (
                kills_by_squad.get(mr.attacker_squad_id, 0) + mr.kills
            )

            _accumulate_weighted_kills(
                weighted_kills_by_squad,
                squads,
                mr.attacker_squad_id,
                mr.defender_squad_id,
                mr.kills,
            )

        # Аккумулируем потери текущего раунда в общую копилку сражения
        for squad_id, count in deaths_by_squad.items():
            battle_state.accumulated_deaths_by_squad[squad_id] = (
                battle_state.accumulated_deaths_by_squad.get(squad_id, 0) + count
            )

        # 6. Мораль, цепная паника, горы трупов и ветеранство
        morale_report = self._combat_service.process_morale_environment_and_veterancy(
            battle_state=battle_state,
            squads=squads,
            all_deaths_by_squad=deaths_by_squad,
            all_kills_by_squad=kills_by_squad,
            all_weighted_kills_by_squad=weighted_kills_by_squad,
        )

        battle_state.clear_orders()
        battle_state.advance_phase(BattlePhase.AFTERMATH)

        # 7. Проверка исхода боя и сборка трофеев
        attacker_alive = sum(
            1
            for s_id in battle_state.attacker_squad_ids
            if s_id in squads
            and squads[s_id].state.unit_count > 0
            and not squads[s_id].state.is_in_panic
        )
        defender_alive = sum(
            1
            for s_id in battle_state.defender_squad_ids
            if s_id in squads
            and squads[s_id].state.unit_count > 0
            and not squads[s_id].state.is_in_panic
        )

        is_finished = attacker_alive == 0 or defender_alive == 0
        victor_faction_id: Optional[str] = None
        loot_site: Optional[BattlefieldLootSite] = None

        if is_finished:
            if attacker_alive > 0 and defender_alive == 0:
                first_attacker_squad = next(
                    (
                        squads[s_id]
                        for s_id in battle_state.attacker_squad_ids
                        if s_id in squads
                    ),
                    None,
                )
                victor_faction_id = (
                    first_attacker_squad.archetype.faction_id if first_attacker_squad else None
                )
            elif defender_alive > 0 and attacker_alive == 0:
                first_defender_squad = next(
                    (
                        squads[s_id]
                        for s_id in battle_state.defender_squad_ids
                        if s_id in squads
                    ),
                    None,
                )
                victor_faction_id = (
                    first_defender_squad.archetype.faction_id if first_defender_squad else None
                )

            salvageable_eq: dict[str, int] = {}
            corpses_list: list[BattlefieldCorpsePile] = []

            # Генерируем трофеи на основе ВСЕХ потерь за весь бой
            total_battle_deaths = sum(battle_state.accumulated_deaths_by_squad.values())

            for squad_id, total_deaths in battle_state.accumulated_deaths_by_squad.items():
                if total_deaths <= 0:
                    continue
                squad = squads.get(squad_id)
                if squad is None:
                    continue

                salvage_count = max(
                    1, int(round(total_deaths * DEFAULT_EQUIPMENT_SALVAGE_RATIO))
                )
                if squad.weapon is not None:
                    salvageable_eq[squad.weapon.id] = (
                        salvageable_eq.get(squad.weapon.id, 0) + salvage_count
                    )
                if squad.armor is not None:
                    salvageable_eq[squad.armor.id] = (
                        salvageable_eq.get(squad.armor.id, 0) + salvage_count
                    )

                corpses_list.append(
                    BattlefieldCorpsePile(
                        race=squad.archetype.race,
                        size_category=squad.size_category,
                        count=total_deaths,
                    )
                )

            loot_site = BattlefieldLootSite(
                hex_coordinates=strategic_hex,
                origin_battle_id=battle_state.id,
                salvageable_equipment=salvageable_eq,
                residual_resonite=float(total_battle_deaths * 0.5),
                corpses=corpses_list,
                ticks_remaining=DEFAULT_BATTLEFIELD_DECAY_TICKS,
            )

            if self._event_bus is not None:
                await self._event_bus.publish(
                    GameEvents.Tactical.BATTLE_COMPLETED,
                    battle_id=battle_state.id,
                    victor_faction_id=victor_faction_id,
                    loot_site_id=loot_site.id,
                )

        return TacticalTurnReport(
            battle_id=battle_state.id,
            tick=battle_state.current_tick,
            phase=battle_state.phase,
            charge_reports=charge_reports,
            movement_reports=movement_reports,
            ranged_reports=ranged_reports,
            melee_reports=melee_reports,
            morale_report=morale_report,
            is_battle_finished=is_finished,
            victor_faction_id=victor_faction_id,
            loot_site=loot_site,
        )
