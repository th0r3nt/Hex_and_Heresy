"""
Определения инструментов тактического боя.
"""

from src.back.l01_domain.llm.models.tools import ToolDefinition
from src.back.l01_domain.llm.tools.schemas.tactical import (
    OrderSquadHoldParams,
    OrderSquadMoveParams,
    OrderSquadReactionParams,
)

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
