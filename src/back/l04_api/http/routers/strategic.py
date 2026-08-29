"""
Глобальный ход, марш армий, назначение рабочих, экспедиции, налоги,
пограничные города и гарнизоны земель.
"""

from fastapi import APIRouter

from src.back.l01_domain.exceptions.factions import FactionNotFoundError
from src.back.l01_domain.factions.models.workers import WorkerAssignment
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.reports import GlobalTurnReport
from src.back.l01_domain.world.models.state import WorldState
from src.back.l04_api.dependencies import Turns, World
from src.back.l04_api.http.schemas.common import OperationResult
from src.back.l04_api.http.schemas.strategic import (
    BorderTownOperationResponse,
    BorderTownResponse,
    ClaimBorderLandRequest,
    ExpeditionRequest,
    FactionVisionResponse,
    FoundBorderTownRequest,
    GarrisonResponse,
    HexVisibilityResponse,
    MarchOrderRequest,
    MarchOrderResponse,
    ResolveBorderTownRequest,
    SetTaxRateRequest,
    StationSquadRequest,
    TaxRateResponse,
    UnstationSquadRequest,
    UpgradeBorderTownRequest,
    VictoryOverviewResponse,
    VictoryProgressResponse,
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
# Туман войны
# ====================================================


def _player_faction_id(world: WorldState) -> str:
    """
    Фракция игрока, за которую и считается туман.

    Партии без игрока не бывает: смотреть на карту глазами некому, поэтому
    запрос слоя тумана в такой партии - честная ошибка, а не пустой ответ.
    """
    player = world.get_player_faction()
    if player is None:
        raise FactionNotFoundError("player")
    return player.id


@router.get("/vision", response_model=FactionVisionResponse)
async def get_vision(turns: Turns, world: World) -> FactionVisionResponse:
    """
    Маска тумана войны активной фракции игрока: что видно сейчас и что
    было открыто раньше.
    """
    vision_map = turns.get_faction_vision(
        world_state=world, faction_id=_player_faction_id(world)
    )
    return FactionVisionResponse.from_vision_map(vision_map)


@router.get("/vision/hex", response_model=HexVisibilityResponse)
async def get_hex_visibility(
    q: int, r: int, turns: Turns, world: World
) -> HexVisibilityResponse:
    """
    Состояние одного гекса глазами игрока - подсказка под курсором на карте.
    """
    faction_id = _player_faction_id(world)
    coord = HexCoordinates.from_axial(q, r)

    return HexVisibilityResponse(
        faction_id=faction_id,
        hex_coordinates=coord,
        state=turns.get_hex_visibility(
            world_state=world, faction_id=faction_id, coord=coord
        ),
    )


@router.get("/world-view", response_model=WorldState)
async def get_world_view(turns: Turns, world: World) -> WorldState:
    """
    Состояние мира глазами игрока.

    В отличие от сырого WorldState, из среза вырезано все, чего разведка не
    видит: чужие армии и караваны вне поля зрения, чужие гонцы, неоткрытые
    места и застройка соседей на неразведанных гексах.
    """
    return turns.get_world_view(world_state=world, faction_id=_player_faction_id(world))


# ====================================================
# Глобальные цели партии
# ====================================================


@router.get("/victory-progress", response_model=VictoryOverviewResponse)
async def get_victory_progress(turns: Turns, world: World) -> VictoryOverviewResponse:
    """
    Панель глобальных целей: насколько игрок и его соперники продвинулись к
    победе по каждой из трех веток.
    """

    def summary(faction_id: str) -> VictoryProgressResponse:
        return VictoryProgressResponse.from_progress(
            progress=turns.get_victory_progress(world, faction_id),
            config=world.victory_config,
            is_finished=world.is_finished,
        )

    player = world.get_player_faction()

    return VictoryOverviewResponse(
        player=None if player is None else summary(player.id),
        rivals=[
            summary(faction.id)
            for faction in world.factions.values()
            if player is None or faction.id != player.id
        ],
    )


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


# ====================================================
# Пограничные города
# ====================================================


@router.post("/border-towns", response_model=BorderTownResponse)
async def found_border_town(
    payload: FoundBorderTownRequest, turns: Turns, world: World
) -> BorderTownResponse:
    """
    Основывает пограничный город на свободном гексе карты. Гарнизон
    поселения поднимется само на ближайшем такте.
    """
    town = await turns.found_border_town(
        world_state=world,
        faction_id=payload.faction_id,
        target_hex=payload.target_hex,
        name=payload.name,
    )
    return BorderTownResponse.from_border_town(town)


@router.post("/border-towns/{town_id}/upgrade", response_model=BorderTownResponse)
async def upgrade_border_town(
    town_id: str, payload: UpgradeBorderTownRequest, turns: Turns, world: World
) -> BorderTownResponse:
    """
    Поднимает город на уровень выше: +1 строительный слот внутри стен.
    Выше четвертого уровня поселение не растет.
    """
    town = await turns.upgrade_border_town(
        world_state=world,
        faction_id=payload.faction_id,
        town_id=town_id,
    )
    return BorderTownResponse.from_border_town(town)


@router.post("/border-towns/{town_id}/claim-land", response_model=BorderTownResponse)
async def claim_border_land(
    town_id: str, payload: ClaimBorderLandRequest, turns: Turns, world: World
) -> BorderTownResponse:
    """
    Выкупает городу смежную свободную землю и ставит на ней ратушу.
    Один город заселяет не больше четырех гексов.
    """
    town = await turns.claim_border_land(
        world_state=world,
        faction_id=payload.faction_id,
        town_id=town_id,
        target_hex=payload.target_hex,
    )
    return BorderTownResponse.from_border_town(town)


@router.get(
    "/factions/{faction_id}/border-towns", response_model=list[BorderTownResponse]
)
async def list_border_towns(
    faction_id: str, turns: Turns, world: World
) -> list[BorderTownResponse]:
    """
    Все пограничные города фракции для окна управления державой.
    """
    towns = turns.list_border_towns(world_state=world, faction_id=faction_id)
    return [BorderTownResponse.from_border_town(town) for town in towns]


# ====================================================
# Судьба побежденного пограничного города
# ====================================================


@router.post(
    "/border-towns/{town_id}/resolve", response_model=BorderTownOperationResponse
)
async def resolve_border_town(
    town_id: str, payload: ResolveBorderTownRequest, turns: Turns, world: World
) -> BorderTownOperationResponse:
    """
    Решает судьбу взятого штурмом города: сжечь, разграбить, занять или
    пройти мимо.

    Разрушение, разграбление и захват занимают 2-3 такта, и все это время
    армия победителя стоит лагерем на гексе города. Пропуск не занимает
    ничего: в ответе на него операции не будет.
    """
    operation = await turns.resolve_border_town(
        world_state=world,
        town_id=town_id,
        army_id=payload.army_id,
        resolution_type=payload.resolution_type,
    )
    if operation is None:
        return BorderTownOperationResponse.idle(town_id)
    return BorderTownOperationResponse.from_operation(operation)


@router.get(
    "/border-towns/{town_id}/operation", response_model=BorderTownOperationResponse
)
async def get_border_town_operation(
    town_id: str, turns: Turns, world: World
) -> BorderTownOperationResponse:
    """
    Прогресс операции над городом для окна осады: сколько тактов осталось
    и что достанется победителю.
    """
    operation = turns.get_border_town_operation(world_state=world, town_id=town_id)
    if operation is None:
        return BorderTownOperationResponse.idle(town_id)
    return BorderTownOperationResponse.from_operation(operation)


# ====================================================
# Гарнизоны земель
# ====================================================


@router.get("/garrisons/{zone_id}", response_model=GarrisonResponse)
async def get_garrison(zone_id: str, turns: Turns, world: World) -> GarrisonResponse:
    """
    Текущий состав гарнизона земли: ополчение, расквартированные войска
    и во что они обходятся казне за такт.
    """
    return GarrisonResponse.from_garrison(turns.get_garrison(world, zone_id))


@router.post("/garrisons/{zone_id}/station", response_model=GarrisonResponse)
async def station_squad(
    zone_id: str, payload: StationSquadRequest, turns: Turns, world: World
) -> GarrisonResponse:
    """
    Оставляет отряд армии за стенами земли. Армия должна стоять на гексе
    гарнизона, а свободные карточки - оставаться в лимите.
    """
    garrison = await turns.station_squad(
        world_state=world,
        army_id=payload.army_id,
        squad_id=payload.squad_id,
        zone_id=zone_id,
    )
    return GarrisonResponse.from_garrison(garrison)


@router.post("/garrisons/{zone_id}/unstation", response_model=GarrisonResponse)
async def unstation_squad(
    zone_id: str, payload: UnstationSquadRequest, turns: Turns, world: World
) -> GarrisonResponse:
    """
    Забирает расквартированный отряд обратно в мобильную армию.
    Городское ополчение вывести нельзя: оно привязано к своей земле.
    """
    await turns.unstation_squad(
        world_state=world,
        army_id=payload.army_id,
        squad_id=payload.squad_id,
        zone_id=zone_id,
    )
    return GarrisonResponse.from_garrison(turns.get_garrison(world, zone_id))
