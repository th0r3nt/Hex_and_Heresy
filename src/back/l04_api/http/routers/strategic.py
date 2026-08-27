"""
Глобальный ход, марш армий, назначение рабочих, экспедиции и налоги.
"""

from fastapi import APIRouter

from src.back.l01_domain.exceptions.factions import FactionNotFoundError
from src.back.l01_domain.factions.models.workers import WorkerAssignment
from src.back.l01_domain.world.models.reports import GlobalTurnReport
from src.back.l04_api.dependencies import Turns, World
from src.back.l04_api.http.schemas.common import OperationResult
from src.back.l04_api.http.schemas.strategic import (
    ExpeditionRequest,
    MarchOrderRequest,
    MarchOrderResponse,
    SetTaxRateRequest,
    TaxRateResponse,
    WorkerAssignRequest,
)

router = APIRouter(prefix="/strategic", tags=["strategic"])


# ====================================================
# Глобальный такт
# ====================================================


@router.post("/turn", response_model=GlobalTurnReport)
async def execute_turn(turns: Turns, world: World) -> GlobalTurnReport:
    """
    Считает глобальный такт: события, экспедиции, экономику, марши и дипломатию.
    """
    return await turns.execute_strategic_turn(world)


# ====================================================
# Приказы армиям
# ====================================================


@router.post("/armies/{army_id}/march", response_model=MarchOrderResponse)
async def order_march(
    army_id: str, payload: MarchOrderRequest, turns: Turns, world: World
) -> MarchOrderResponse:
    """
    Прокладывает армии маршрут. Сам марш произойдет на ближайшем такте.
    """
    path = turns.order_army_march(
        world_state=world,
        army_id=army_id,
        target_hex=payload.target_hex,
    )
    return MarchOrderResponse(army_id=army_id, planned_path=path)


# ====================================================
# Налоги
# ====================================================


@router.get("/factions/{faction_id}/tax-rate", response_model=TaxRateResponse)
async def get_tax_rate(faction_id: str, world: World) -> TaxRateResponse:
    """
    Текущее положение налогового ползунка и его последствия для подданных.
    """
    faction = world.get_faction(faction_id)
    if faction is None:
        raise FactionNotFoundError(faction_id)
    return TaxRateResponse.from_faction(faction)


@router.put("/factions/{faction_id}/tax-rate", response_model=TaxRateResponse)
async def set_tax_rate(
    faction_id: str, payload: SetTaxRateRequest, turns: Turns, world: World
) -> TaxRateResponse:
    """
    Двигает ползунок налога. Сбор по новой ставке пойдет со следующего такта.
    """
    faction = await turns.set_faction_tax_rate(
        world_state=world,
        faction_id=faction_id,
        rate=payload.rate,
    )
    return TaxRateResponse.from_faction(faction)


# ====================================================
# Рабочие и экспедиции
# ====================================================


@router.post("/workers/assign", response_model=WorkerAssignment)
async def assign_worker(
    payload: WorkerAssignRequest, turns: Turns, world: World
) -> WorkerAssignment:
    """Ставит отряд рабочих на экономическое здание."""
    return await turns.assign_worker(
        world_state=world,
        squad_id=payload.squad_id,
        faction_id=payload.faction_id,
        building_id=payload.building_id,
    )


@router.post("/workers/{squad_id}/unassign", response_model=OperationResult)
async def unassign_worker(squad_id: str, turns: Turns, world: World) -> OperationResult:
    """Снимает отряд рабочих с производства."""
    await turns.unassign_worker(world_state=world, squad_id=squad_id)
    return OperationResult(detail=f"Отряд '{squad_id}' снят с работ.")


@router.post("/workers/expedition", response_model=WorkerAssignment)
async def dispatch_expedition(
    payload: ExpeditionRequest, turns: Turns, world: World
) -> WorkerAssignment:
    """Отправляет караван рабочих на нейтральный гекс."""
    return await turns.dispatch_expedition(
        world_state=world,
        squad_id=payload.squad_id,
        faction_id=payload.faction_id,
        target_hex=payload.target_hex,
        home_hex=payload.home_hex,
        mining_duration_ticks=payload.mining_duration_ticks,
    )
