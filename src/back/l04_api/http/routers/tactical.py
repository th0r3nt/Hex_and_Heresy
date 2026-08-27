"""
Тактический бой: расстановка, приказы отрядам и расчет раундов.

Состояние идущего боя живет в контексте перехода конечного автомата, поэтому
между запросами его достает зависимость get_battle_state, а не клиент.
"""

from fastapi import APIRouter

from src.back.l01_domain.combat.models.reports import TacticalTurnReport
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l04_api.dependencies import Battle, GameFlow, Turns, World
from src.back.l04_api.http.schemas.common import OperationResult
from src.back.l04_api.http.schemas.tactical import (
    BattleFinishRequest,
    BattleOrdersRequest,
    BattleStartRequest,
)

router = APIRouter(prefix="/tactical", tags=["tactical"])


# ====================================================
# Жизненный цикл боя
# ====================================================


@router.post("/battles", response_model=TacticalBattleState)
async def start_battle(
    payload: BattleStartRequest, gameflow: GameFlow
) -> TacticalBattleState:
    """
    Начинает бой: переводит режим игры и запирает армии сторон на гексе.
    """
    await gameflow.enter_tactical_combat(
        hex_coords=payload.hex_coordinates,
        attacker_faction_id=payload.attacker_faction_id,
        defender_faction_id=payload.defender_faction_id,
        battle_state=payload.battle_state,
    )
    return payload.battle_state


@router.get("/battles/current", response_model=TacticalBattleState)
async def get_current_battle(battle: Battle) -> TacticalBattleState:
    """Состояние идущего боя: сетка, фаза, расстановка."""
    return battle


@router.post("/battles/current/finish", response_model=OperationResult)
async def finish_battle(
    payload: BattleFinishRequest, battle: Battle, gameflow: GameFlow
) -> OperationResult:
    """Закрывает бой и возвращает игру на глобальную карту."""
    await gameflow.finish_tactical_combat(
        battle_id=battle.id,
        victor_faction_id=payload.victor_faction_id,
        is_base_destroyed=payload.is_base_destroyed,
    )
    return OperationResult(detail=f"Бой '{battle.id}' завершен.")


# ====================================================
# Приказы и расчет раунда
# ====================================================


@router.post("/battles/current/orders", response_model=OperationResult)
async def queue_orders(payload: BattleOrdersRequest, battle: Battle) -> OperationResult:
    """
    Копит приказы отрядам до расчета раунда: стороны ходят одновременно.
    """
    if payload.replace_pending:
        battle.clear_orders()

    for order in payload.orders:
        battle.queue_order(order)

    return OperationResult(detail=f"Принято приказов: {len(battle.pending_orders)}.")


@router.post("/battles/current/turn", response_model=TacticalTurnReport)
async def execute_turn(turns: Turns, world: World, battle: Battle) -> TacticalTurnReport:
    """
    Считает один тактический раунд (30 секунд) по накопленным приказам.
    """
    return await turns.execute_tactical_turn(world_state=world, battle_state=battle)
