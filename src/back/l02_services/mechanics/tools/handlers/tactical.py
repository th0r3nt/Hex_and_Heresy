"""
Обработчики навыков тактического боя.
"""

from typing import Any

from src.back.l01_domain.combat.constants import (
    SPEED_DEFENSE_PACE,
    TACTICAL_PACE_SPEEDS,
)
from src.back.l01_domain.combat.models.state import (
    SquadOrder,
    TacticalBattleState,
    TacticalCellState,
)
from src.back.l01_domain.exceptions.combat import OrderNotAllowedError
from src.back.l01_domain.llm.tools.definitions.tactical import (
    ORDER_SQUAD_HOLD,
    ORDER_SQUAD_MOVE,
    ORDER_SQUAD_REACTION,
)
from src.back.l01_domain.llm.tools.schemas.tactical import (
    OrderSquadHoldParams,
    OrderSquadMoveParams,
    OrderSquadReactionParams,
)
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor


class TacticalToolHandlers:
    """
    Приказы отрядам в WEGO-бою.

    Фасада у набора нет: приказ кладется прямо в очередь боевого состояния,
    которое приезжает в контексте исполнения.
    """

    def register(self, executor: ToolExecutor) -> None:
        """
        Подключает тактические навыки к исполнителю.
        """
        executor.register_handler(ORDER_SQUAD_MOVE, self.order_squad_move)
        executor.register_handler(ORDER_SQUAD_HOLD, self.order_squad_hold)
        executor.register_handler(ORDER_SQUAD_REACTION, self.order_squad_reaction)

    # ====================================================
    # Навыки
    # ====================================================

    async def order_squad_move(
        self, params: OrderSquadMoveParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Ставит в очередь приказ на перемещение или атаку отряда с заданным темпом.
        """
        battle_state = ctx.require_battle_state("order_squad_move")
        target_cell = params.to_target_cell()
        pace_speed = TACTICAL_PACE_SPEEDS[params.pace]

        order = SquadOrder(
            squad_id=params.squad_id,
            target_cell=target_cell,
            pace=pace_speed,
        )
        battle_state.queue_order(order)

        return (
            f"Отряду '{params.squad_id}' отдан приказ переместиться на клетку ({params.target_x}, {params.target_y}) "
            f"с темпом '{params.pace.value}'.",
            {
                "squad_id": params.squad_id,
                "target_cell": target_cell.to_tuple(),
                "pace": params.pace.value,
            },
        )

    async def order_squad_hold(
        self, params: OrderSquadHoldParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Ставит в очередь приказ удерживать текущую позицию в глухой обороне.
        """
        battle_state = ctx.require_battle_state("order_squad_hold")
        current_cell = self._locate_squad(battle_state, params.squad_id)

        order = SquadOrder(
            squad_id=params.squad_id,
            target_cell=current_cell.coordinates,
            pace=SPEED_DEFENSE_PACE,
        )
        battle_state.queue_order(order)

        return (
            f"Отряду '{params.squad_id}' отдан приказ удерживать позицию в обороне.",
            {
                "squad_id": params.squad_id,
                "current_cell": current_cell.coordinates.to_tuple(),
            },
        )

    async def order_squad_reaction(
        self, params: OrderSquadReactionParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Назначает защищающемуся отряду реакцию на вражеский натиск.
        """
        battle_state = ctx.require_battle_state("order_squad_reaction")
        current_cell = self._locate_squad(battle_state, params.squad_id)

        target_cell = params.to_target_cell() or current_cell.coordinates
        order = SquadOrder(
            squad_id=params.squad_id,
            target_cell=target_cell,
            pace=SPEED_DEFENSE_PACE,
            reaction=params.reaction,
        )
        battle_state.queue_order(order)

        return (
            f"Отряду '{params.squad_id}' назначена реакция на натиск: '{params.reaction.value}'.",
            {"squad_id": params.squad_id, "reaction": params.reaction.value},
        )

    # ====================================================
    # Служебное
    # ====================================================

    @staticmethod
    def _locate_squad(
        battle_state: TacticalBattleState, squad_id: str
    ) -> TacticalCellState:
        """
        Находит клетку отряда на поле боя: без нее приказ отдавать некому.
        """
        cell = next(
            (c for c in battle_state.cells if c.occupant_squad_id == squad_id),
            None,
        )
        if cell is None:
            raise OrderNotAllowedError(squad_id, "отряд не найден на поле боя")
        return cell
