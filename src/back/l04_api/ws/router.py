"""
Эндпоинт подключения к каналу уведомлений.

Соединение живет, пока открыто окно клиента: сервер вещает в него события
мира, а клиент только держит канал живым пингами. Игровых команд здесь нет -
они идут обычным HTTP.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from src.back.l04_api.ws.manager import ConnectionManager
from src.back.l04_api.ws.schemas import (
    CONNECTION_ESTABLISHED,
    CONNECTION_PONG,
    ClientMessage,
    ServerMessage,
)
from src.back.utils.logger import main_logger

router = APIRouter(tags=["websocket"])

PING_ACTION = "ping"


def get_connection_manager(websocket: WebSocket) -> ConnectionManager:
    """
    Менеджер соединений, положенный в app.state при старте приложения.

    Отдельная функция, а не dependencies.py: там живут фасады прикладного
    слоя, а это - деталь самого канала.
    """
    return websocket.app.state.ws_manager


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Канал уведомлений о жизни мира.
    """
    manager = get_connection_manager(websocket)
    await manager.connect(websocket)

    try:
        await manager.send_personal(
            websocket, ServerMessage(event=CONNECTION_ESTABLISHED)
        )

        while True:
            raw = await websocket.receive_json()
            await _handle_client_message(manager, websocket, raw)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as error:
        main_logger.warning(f"[WS] Канал закрыт с ошибкой: {error}")
        manager.disconnect(websocket)


async def _handle_client_message(
    manager: ConnectionManager, websocket: WebSocket, raw: object
) -> None:
    """
    Разбирает входящее сообщение.

    Мусор в канале не повод рвать соединение: неизвестное сообщение молча
    игнорируется, чтобы окно клиента не отваливалось из-за опечатки.
    """
    try:
        message = ClientMessage.model_validate(raw)
    except ValidationError:
        main_logger.debug(f"[WS] Непонятное сообщение от клиента: {raw!r}")
        return

    if message.action == PING_ACTION:
        await manager.send_personal(websocket, ServerMessage(event=CONNECTION_PONG))
