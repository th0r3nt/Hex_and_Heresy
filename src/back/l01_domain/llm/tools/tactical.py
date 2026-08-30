"""
Инструменты тактического сеточного боя.
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.combat.constants import ReactionType, TacticalMovementPace
from src.back.l01_domain.llm.models.skills import ToolDefinition
from src.back.l01_domain.maps.models.tactical import CellCoordinates


class OrderSquadMoveParams(BaseModel):
    """Параметры приказа на перемещение или атаку отряда в бою."""

    squad_id: str = Field(..., min_length=1, description="Идентификатор командуемого отряда")
    target_x: int = Field(..., ge=0, description="Координата X целевой клетки сетки")
    target_y: int = Field(..., ge=0, description="Координата Y целевой клетки сетки")
    pace: TacticalMovementPace = Field(
        default=TacticalMovementPace.MARCH,
        description="Темп перемещения: defense, tactical, slow, march, charge",
    )

    def to_target_cell(self) -> CellCoordinates:
        return CellCoordinates(x=self.target_x, y=self.target_y)


class OrderSquadHoldParams(BaseModel):
    """Параметры приказа отряду удерживать текущую позицию в обороне."""

    squad_id: str = Field(..., min_length=1, description="Идентификатор отряда")


class OrderSquadReactionParams(BaseModel):
    """Параметры встречной реакции защищающегося отряда на натиск."""

    squad_id: str = Field(..., min_length=1, description="Идентификатор защищающегося отряда")
    reaction: ReactionType = Field(
        ..., description="Тип реакции: accept_charge, counter_charge, flee"
    )
    target_x: Optional[int] = Field(
        default=None, ge=0, description="Опциональная координата X клетки реакции"
    )
    target_y: Optional[int] = Field(
        default=None, ge=0, description="Опциональная координата Y клетки реакции"
    )

    def to_target_cell(self) -> Optional[CellCoordinates]:
        if self.target_x is not None and self.target_y is not None:
            return CellCoordinates(x=self.target_x, y=self.target_y)
        return None


ORDER_SQUAD_MOVE = ToolDefinition(
    name="order_squad_move",
    description="Отдать приказ отряду на перемещение или атаку цели на тактической сетке с заданным темпом.",
    parameters_model=OrderSquadMoveParams,
)

ORDER_SQUAD_HOLD = ToolDefinition(
    name="order_squad_hold",
    description="Приказать отряду оставаться на позиции в глухой обороне, повышая защиту.",
    parameters_model=OrderSquadHoldParams,
)

ORDER_SQUAD_REACTION = ToolDefinition(
    name="order_squad_reaction",
    description="Назначить реакцию отряда на вражеский натиск (принять на копья, встречный натиск или бегство).",
    parameters_model=OrderSquadReactionParams,
)
