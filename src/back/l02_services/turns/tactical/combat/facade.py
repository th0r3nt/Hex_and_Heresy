"""
Координирующий сервис тактического боя.
"""

from typing import Optional

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import TerrainType
from src.back.l01_domain.combat.models.effects import TerrainProfile
from src.back.l01_domain.combat.models.reports import (
    ChargeStepReport,
    MeleeCombatReport,
    MoraleAndEnvironmentReport,
    RangedCombatReport,
)
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l02_services.turns.tactical.combat.charges import TacticalChargeService
from src.back.l02_services.turns.tactical.combat.melee import TacticalMeleeService
from src.back.l02_services.turns.tactical.combat.morale import (
    TacticalMoraleEnvironmentService,
)
from src.back.l02_services.turns.tactical.combat.ranged import TacticalRangedService


class TacticalCombatService:
    """
    Фасад боевой подсистемы: объединяет расчет натиска, стрельбы,
    рукопашных столкновений и психологии окружения.
    """

    def __init__(
        self,
        charge_service: Optional[TacticalChargeService] = None,
        ranged_service: Optional[TacticalRangedService] = None,
        melee_service: Optional[TacticalMeleeService] = None,
        morale_service: Optional[TacticalMoraleEnvironmentService] = None,
    ) -> None:
        self._charge_service = charge_service or TacticalChargeService()
        self._ranged_service = ranged_service or TacticalRangedService()
        self._melee_service = melee_service or TacticalMeleeService()
        self._morale_service = morale_service or TacticalMoraleEnvironmentService()

    def reset_battle_accumulators(self) -> None:
        self._morale_service.reset_accumulators()

    # =======================================================================
    # Расчет натиска
    # =======================================================================

    def resolve_charges(
        self,
        battle_state: TacticalBattleState,
        squads: dict[str, Squad],
        terrain_profiles: Optional[dict[TerrainType, TerrainProfile]] = None,
    ) -> list[ChargeStepReport]:
        return self._charge_service.resolve_charges(
            battle_state=battle_state,
            squads=squads,
            terrain_profiles=terrain_profiles,
        )

    # =======================================================================
    # Расчет дальних атак
    # =======================================================================

    def resolve_ranged_combat(
        self,
        battle_state: TacticalBattleState,
        squads: dict[str, Squad],
        terrain_profiles: Optional[dict[TerrainType, TerrainProfile]] = None,
    ) -> list[RangedCombatReport]:
        return self._ranged_service.resolve_ranged_attacks(
            battle_state=battle_state,
            squads=squads,
            terrain_profiles=terrain_profiles,
        )

    # =======================================================================
    # Расчет ближних атак
    # =======================================================================

    def resolve_melee_combat(
        self,
        battle_state: TacticalBattleState,
        squads: dict[str, Squad],
    ) -> list[MeleeCombatReport]:
        return self._melee_service.resolve_melee_clashes(
            battle_state=battle_state,
            squads=squads,
        )

    # =======================================================================
    # Расчет морали
    # =======================================================================

    def process_morale_environment_and_veterancy(
        self,
        battle_state: TacticalBattleState,
        squads: dict[str, Squad],
        all_deaths_by_squad: dict[str, int],
        all_kills_by_squad: dict[str, int],
        all_weighted_kills_by_squad: dict[str, float],
    ) -> MoraleAndEnvironmentReport:
        return self._morale_service.process_morale_and_environment(
            battle_state=battle_state,
            squads=squads,
            all_deaths_by_squad=all_deaths_by_squad,
            all_kills_by_squad=all_kills_by_squad,
            all_weighted_kills_by_squad=all_weighted_kills_by_squad,
        )
