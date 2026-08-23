"""
Доменные модели отчетов и результатов тактического боя и стратегических столкновений.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from src.back.l01_domain.combat.constants import BattlePhase, FacingAngle, ReactionType
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l01_domain.world.models.battleground import BattlefieldLootSite

# ==================================================================
# СТРАТЕГИЧЕСКИЕ СТОЛКНОВЕНИЯ И ПЕРЕМЕЩЕНИЯ
# ==================================================================


class EncounterEvent(BaseModel):
    """
    Событие боевого столкновения двух армий на гексе глобальной карты.
    """

    model_config = ConfigDict(frozen=True)

    hex_coordinates: HexCoordinates = Field(...)
    faction_a_id: str = Field(...)
    faction_b_id: str = Field(...)
    army_a_id: str = Field(...)
    army_b_id: str = Field(...)
    is_ambush: bool = Field(default=False)
    ambusher_army_id: Optional[str] = Field(default=None)


class MovementStepReport(BaseModel):
    """
    Отчет о результатах фазы стратегических перемещений и столкновений.
    Дипломатическая логистика (гонцы, послы) живет в DiplomacyTickReport.
    """

    model_config = ConfigDict(frozen=True)

    moved_army_ids: list[str] = Field(default_factory=list)
    encounters: list[EncounterEvent] = Field(default_factory=list)


# ==================================================================
# ТАКТИЧЕСКИЙ БОЙ
# ==================================================================


class ChargeStepReport(BaseModel):
    """
    Отчет о разрешении фазы натиска.
    """

    model_config = ConfigDict(frozen=True)

    attacker_squad_id: str = Field(...)
    defender_squad_id: str = Field(...)
    reaction: ReactionType = Field(...)
    damage_to_attacker: float = Field(default=0.0)
    damage_to_defender: float = Field(default=0.0)
    attacker_deaths: int = Field(default=0)
    defender_deaths: int = Field(default=0)
    defender_morale_shock: float = Field(default=0.0)


class MovementActionReport(BaseModel):
    """
    Отчет о перемещении одного отряда за такт.
    """

    model_config = ConfigDict(frozen=True)

    squad_id: str = Field(...)
    start_cell: CellCoordinates = Field(...)
    end_cell: CellCoordinates = Field(...)
    path_taken: list[CellCoordinates] = Field(default_factory=list)
    stamina_spent: float = Field(default=0.0)
    is_formation_broken: bool = Field(default=False)
    was_blocked: bool = Field(default=False)
    is_fleeing: bool = Field(default=False)


class RangedCombatReport(BaseModel):
    """
    Отчет о дистанционной атаке.
    """

    model_config = ConfigDict(frozen=True)

    attacker_squad_id: str = Field(...)
    target_cell: CellCoordinates = Field(...)
    target_squad_id: Optional[str] = Field(default=None)
    damage_dealt: float = Field(default=0.0)
    kills: int = Field(default=0)
    is_misfire: bool = Field(default=False)
    friendly_fire_kills: int = Field(default=0)
    friendly_fire_squad_id: Optional[str] = Field(default=None)
    cover_reduction: float = Field(default=0.0)


class MeleeCombatReport(BaseModel):
    """
    Отчет о рукопашной схватке.
    """

    model_config = ConfigDict(frozen=True)

    attacker_squad_id: str = Field(...)
    defender_squad_id: str = Field(...)
    damage_dealt: float = Field(default=0.0)
    kills: int = Field(default=0)
    flank_angle: FacingAngle = Field(default=FacingAngle.FRONT)


class MoraleAndEnvironmentReport(BaseModel):
    """
    Отчет об изменении морали, цепной панике, горах трупов и ветеранстве.
    """

    model_config = ConfigDict(frozen=True)

    panicking_squad_ids: list[str] = Field(default_factory=list)
    chain_panic_shocks: dict[str, float] = Field(default_factory=dict)
    new_corpse_piles: list[CellCoordinates] = Field(default_factory=list)
    veterancy_candidate_ids: list[str] = Field(default_factory=list)


class TacticalTurnReport(BaseModel):
    """
    Итоговый отчет о результатах тактического раунда (30 секунд боя).
    """

    model_config = ConfigDict(frozen=True)

    battle_id: str = Field(...)
    tick: int = Field(...)
    phase: BattlePhase = Field(...)

    charge_reports: list[ChargeStepReport] = Field(default_factory=list)
    movement_reports: list[MovementActionReport] = Field(default_factory=list)
    ranged_reports: list[RangedCombatReport] = Field(default_factory=list)
    melee_reports: list[MeleeCombatReport] = Field(default_factory=list)
    morale_report: MoraleAndEnvironmentReport = Field(...)

    is_battle_finished: bool = Field(default=False)
    victor_faction_id: Optional[str] = Field(default=None)
    loot_site: Optional[BattlefieldLootSite] = Field(default=None)
