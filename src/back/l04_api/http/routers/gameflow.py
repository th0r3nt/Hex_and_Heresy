"""
Управление режимами игры: старт партии, пауза, служебные экраны и финал.

Переходы проверяет конечный автомат внутри фасада, поэтому обработчики
только передают ему триггер и возвращают новое состояние.
"""

from fastapi import APIRouter, HTTPException, Request, status

from src.back.l02_services.gameflow.facade import GameFlowFacade
from src.back.l02_services.gameflow.states import GameState
from src.back.l04_api.dependencies import GameFlow, World, get_container
from src.back.l04_api.http.schemas.gameflow import (
    DiplomaticSessionRequest,
    GameOverRequest,
    GameStateResponse,
    GlobalEventScreenRequest,
)

router = APIRouter(prefix="/gameflow", tags=["gameflow"])


def _as_response(facade: GameFlowFacade) -> GameStateResponse:
    return GameStateResponse(
        state=facade.current_state,
        is_party_active=facade.world_state is not None,
    )


# ====================================================
# Текущий режим
# ====================================================


@router.get("/state", response_model=GameStateResponse)
async def get_state(gameflow: GameFlow) -> GameStateResponse:
    """Текущее состояние конечного автомата."""
    return _as_response(gameflow)


# ====================================================
# Старт партии
# ====================================================


@router.post("/new-game", response_model=GameStateResponse)
async def start_new_game(gameflow: GameFlow) -> GameStateResponse:
    """
    Переводит игру из меню на глобальную карту.

    Мир новой партии сюда еще не приезжает: генератора мира в проекте нет,
    и привязку WorldState делает корень компоновки (bind_world_state) сразу
    после его появления. До этого игровые эндпоинты отвечают 409.
    """
    await gameflow.start_new_game()
    return _as_response(gameflow)


# ====================================================
# Пауза и служебные экраны
# ====================================================


@router.post("/pause", response_model=GameStateResponse)
async def pause_game(gameflow: GameFlow) -> GameStateResponse:
    await gameflow.pause_game()
    return _as_response(gameflow)


@router.post("/resume", response_model=GameStateResponse)
async def resume_game(gameflow: GameFlow) -> GameStateResponse:
    await gameflow.resume_game()
    return _as_response(gameflow)


@router.post("/settings/open", response_model=GameStateResponse)
async def open_settings(gameflow: GameFlow) -> GameStateResponse:
    await gameflow.open_settings()
    return _as_response(gameflow)


@router.post("/settings/close", response_model=GameStateResponse)
async def close_settings(gameflow: GameFlow) -> GameStateResponse:
    await gameflow.close_settings()
    return _as_response(gameflow)


@router.post("/credits/open", response_model=GameStateResponse)
async def open_credits(gameflow: GameFlow) -> GameStateResponse:
    await gameflow.open_credits()
    return _as_response(gameflow)


@router.post("/credits/close", response_model=GameStateResponse)
async def close_credits(gameflow: GameFlow) -> GameStateResponse:
    await gameflow.close_credits()
    return _as_response(gameflow)


# ====================================================
# Дипломатическая аудиенция
# ====================================================


@router.post("/audience/open", response_model=GameStateResponse)
async def open_audience(
    payload: DiplomaticSessionRequest, gameflow: GameFlow
) -> GameStateResponse:
    await gameflow.open_diplomatic_session(
        initiator_faction_id=payload.initiator_faction_id,
        target_faction_id=payload.target_faction_id,
        ambassador_id=payload.ambassador_id,
    )
    return _as_response(gameflow)


@router.post("/audience/close", response_model=GameStateResponse)
async def close_audience(gameflow: GameFlow) -> GameStateResponse:
    await gameflow.close_diplomatic_session()
    return _as_response(gameflow)


# ====================================================
# Окно глобального события
# ====================================================


@router.post("/global-event/show", response_model=GameStateResponse)
async def show_global_event(
    payload: GlobalEventScreenRequest, gameflow: GameFlow, world: World
) -> GameStateResponse:
    """Открывает модальное окно уже существующего кризиса мира."""
    event = next((e for e in world.active_events if e.id == payload.event_id), None)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Событие '{payload.event_id}' не найдено среди активных.",
        )

    await gameflow.show_global_event(event)
    return _as_response(gameflow)


@router.post("/global-event/resolve", response_model=GameStateResponse)
async def resolve_global_event(gameflow: GameFlow) -> GameStateResponse:
    await gameflow.resolve_global_event()
    return _as_response(gameflow)


# ====================================================
# Финал партии
# ====================================================


@router.post("/game-over", response_model=GameStateResponse)
async def declare_game_over(
    payload: GameOverRequest, gameflow: GameFlow
) -> GameStateResponse:
    await gameflow.trigger_game_over(
        is_player_victorious=payload.is_player_victorious,
        reason=payload.reason,
        total_ticks=payload.total_ticks,
    )
    return _as_response(gameflow)


@router.post("/quit-to-menu", response_model=GameStateResponse)
async def quit_to_main_menu(request: Request, gameflow: GameFlow) -> GameStateResponse:
    """
    Выходит в главное меню.

    Мир завершенной партии отвязывается от всех сервисов, которые его
    держали, - список знает только корень компоновки.
    """
    await gameflow.quit_to_main_menu()
    get_container(request).unbind_session()
    return GameStateResponse(state=GameState.MAIN_MENU, is_party_active=False)
