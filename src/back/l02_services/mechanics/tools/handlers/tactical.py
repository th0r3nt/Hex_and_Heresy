"""
Обработчики приказов тактического боя.

Приказ только встает в очередь раунда: расчет идет одновременно для обеих
сторон, поэтому навык ничего не двигает сам. Бой берется из обстановки -
вне боя приказывать отрядам нечего.
"""

from typing import Optional

from src.back.l01_domain.combat.constants import TACTICAL_PACE_SPEEDS, SPEED_DEFENSE_PACE
from src.back.l01_domain.combat.models.state import SquadOrder, TacticalBattleState
from src.back.l01_domain.exceptions.llm import ToolContextMissingError
from src.back.l01_domain.llm.tools.tactical import (
    ORDER_SQUAD_HOLD,
    ORDER_SQUAD_MOVE,
    ORDER_SQUAD_REACTION,
    OrderSquadHoldParams,
    OrderSquadMoveParams,
    OrderSquadReactionParams,
)
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor


def _require_battle(
    context: ToolExecutionContext, tool_name: str
) -> TacticalBattleState:
    """Бой, в котором отдается приказ."""
    if context.battle_state is None:
        raise ToolContextMissingError(tool_name, "о каком бое идет речь")
    return context.battle_state


def _require_own_cell(
    battle: TacticalBattleState, squad_id: str, tool_name: str
) -> CellCoordinates:
    """Клетка, на которой отряд стоит прямо сейчас."""
    cell: Optional[CellCoordinates] = next(
        (
            state.coordinates
            for state in battle.cells
            if state.occupant_squad_id == squad_id
        ),
        None,
    )
    if cell is None:
        raise ToolContextMissingError(tool_name, f"где на поле стоит отряд '{squad_id}'")
    return cell


def register_tactical_handlers(executor: ToolExecutor) -> None:
    """
    Подключает приказы тактического боя к диспетчеру.
    """

    async def order_squad_move(
        context: ToolExecutionContext, params: OrderSquadMoveParams
    ) -> str:
        battle = _require_battle(context, ORDER_SQUAD_MOVE.name)
        battle.queue_order(
            SquadOrder(
                squad_id=params.squad_id,
                target_cell=params.to_target_cell(),
                pace=TACTICAL_PACE_SPEEDS[params.pace],
            )
        )
        return (
            f"Отряд '{params.squad_id}' пойдет к клетке "
            f"({params.target_x}, {params.target_y}) темпом '{params.pace.value}'."
        )

    async def order_squad_hold(
        context: ToolExecutionContext, params: OrderSquadHoldParams
    ) -> str:
        battle = _require_battle(context, ORDER_SQUAD_HOLD.name)
        # Держать позицию - это приказ идти в собственную клетку с нулевым
        # темпом: отдельного вида приказа домену для этого не нужно
        battle.queue_order(
            SquadOrder(
                squad_id=params.squad_id,
                target_cell=_require_own_cell(
                    battle, params.squad_id, ORDER_SQUAD_HOLD.name
                ),
                pace=SPEED_DEFENSE_PACE,
            )
        )
        return f"Отряд '{params.squad_id}' держит позицию."

    async def order_squad_reaction(
        context: ToolExecutionContext, params: OrderSquadReactionParams
    ) -> str:
        battle = _require_battle(context, ORDER_SQUAD_REACTION.name)
        # Принять удар на копья можно только там, где стоишь, поэтому клетка
        # реакции необязательна: без нее отряд остается на месте
        target_cell = params.to_target_cell() or _require_own_cell(
            battle, params.squad_id, ORDER_SQUAD_REACTION.name
        )
        battle.queue_order(
            SquadOrder(
                squad_id=params.squad_id,
                target_cell=target_cell,
                pace=SPEED_DEFENSE_PACE,
                reaction=params.reaction,
            )
        )
        return (
            f"Отряд '{params.squad_id}' встретит натиск реакцией "
            f"'{params.reaction.value}'."
        )

    executor.register(ORDER_SQUAD_MOVE, order_squad_move)
    executor.register(ORDER_SQUAD_HOLD, order_squad_hold)
    executor.register(ORDER_SQUAD_REACTION, order_squad_reaction)


__all__ = ["register_tactical_handlers"]
