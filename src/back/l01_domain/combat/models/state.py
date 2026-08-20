"""
Динамическое состояние конкретного тактического боя.

Геометрия сетки (клетки, соседство) - забота maps/models/tactical.py;
здесь хранится только то, что специфично для именно этого боя: кто где стоит,
какая сейчас фаза, погода, время суток, активные эффекты.
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.combat.constants import (
    BattleMapSize,
    BattlePhase,
    ReactionType,
    WeatherCondition,
    TimeOfDay,
    TerrainType,
    EffectStackingRule,
    SPEED_MARCH_PACE,
)
from src.back.l01_domain.combat.models.effects import CombatEffect
from src.back.l01_domain.maps.models.tactical import CellCoordinates


class TacticalCellState(BaseModel):
    """
    Динамическое состояние одной клетки сетки в текущем бою.
    """

    coordinates: CellCoordinates = Field(...)
    terrain_type: TerrainType = Field(default=TerrainType.PLAIN)
    occupant_squad_id: Optional[str] = Field(
        default=None, description="ID отряда/героя, стоящего на клетке"
    )
    active_effects: list[CombatEffect] = Field(default_factory=list)

    def add_effect(self, effect: CombatEffect) -> None:
        """
        Накладывает эффект на клетку с учётом stacking_rule.
        """

        already_present = any(e.id == effect.id for e in self.active_effects)

        if effect.stacking_rule == EffectStackingRule.IGNORE and already_present:
            return
        if effect.stacking_rule == EffectStackingRule.REFRESH:
            self.active_effects = [e for e in self.active_effects if e.id != effect.id]

        self.active_effects.append(effect)

    def remove_effect(self, effect_id: str) -> None:
        self.active_effects = [e for e in self.active_effects if e.id != effect_id]


class DeploymentZone(BaseModel):
    """
    Зона, доступная стороне для расстановки войск перед боем.
    """

    model_config = ConfigDict(frozen=True)

    side: str = Field(..., description="'attacker' или 'defender'")
    cells: list[CellCoordinates] = Field(default_factory=list)


class SquadOrder(BaseModel):
    """
    Приказ игрока конкретному отряду на текущий ход.
    """

    squad_id: str = Field(..., min_length=1)
    target_cell: CellCoordinates = Field(...)
    pace: float = Field(default=SPEED_MARCH_PACE, ge=0)
    reaction: Optional[ReactionType] = Field(
        default=None,
        description="Заполняется, если это реакция защищающегося, а не приказ атакующего",
    )


class TacticalBattleState(BaseModel):
    """
    Агрегат состояния тактического боя.
    Мутируется на каждый расчёт хода в l02_services/turns/tactical.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    map_size: BattleMapSize = Field(default=BattleMapSize.MEDIUM)

    cells: list[TacticalCellState] = Field(default_factory=list)
    deployment_zones: list[DeploymentZone] = Field(default_factory=list)

    current_tick: int = Field(default=0, ge=0)
    phase: BattlePhase = Field(default=BattlePhase.DEPLOYMENT)
    weather: WeatherCondition = Field(default=WeatherCondition.CLEAR)
    time_of_day: TimeOfDay = Field(default=TimeOfDay.GREY_HOURS)

    pending_orders: list[SquadOrder] = Field(default_factory=list)

    attacker_squad_ids: list[str] = Field(default_factory=list)
    defender_squad_ids: list[str] = Field(default_factory=list)

    accumulated_deaths_by_squad: dict[str, int] = Field(
        default_factory=dict,
        description="Накопитель потерь отрядов за все раунды боя для генерации поля брани",
    )

    def get_cell(self, coordinates: CellCoordinates) -> Optional[TacticalCellState]:
        return next((c for c in self.cells if c.coordinates == coordinates), None)

    def advance_phase(self, next_phase: BattlePhase) -> None:
        self.phase = next_phase

    def queue_order(self, order: SquadOrder) -> None:
        self.pending_orders.append(order)

    def clear_orders(self) -> None:
        self.pending_orders.clear()
