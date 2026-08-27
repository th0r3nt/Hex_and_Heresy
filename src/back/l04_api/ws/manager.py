"""
Менеджер активных WebSocket-соединений.

Клиент у игры один - окно Electron, но соединений может оказаться больше
(переподключение, вторая вкладка при отладке), поэтому менеджер держит их
множеством и рассылает сообщение всем сразу.
"""

from fastapi import WebSocket

from src.back.l04_api.ws.schemas import ServerMessage
from src.back.utils.logger import main_logger


class ConnectionManager:
    """
    Хранит живые соединения и вещает в них сообщения сервера.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    @property
    def connections_count(self) -> int:
        """Число живых соединений - для диагностики и тестов."""
        return len(self._connections)

    # ==================================================================
    # ЖИЗНЕННЫЙ ЦИКЛ СОЕДИНЕНИЯ
    # ==================================================================

    async def connect(self, websocket: WebSocket) -> None:
        """
        Принимает рукопожатие и берет соединение под учет.
        """
        await websocket.accept()
        self._connections.add(websocket)
        main_logger.debug(
            f"[WS] Клиент подключен. Живых соединений: {len(self._connections)}."
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Снимает соединение с учета. Повторный вызов безопасен.
        """
        self._connections.discard(websocket)
        main_logger.debug(
            f"[WS] Клиент отключен. Живых соединений: {len(self._connections)}."
        )

    # ==================================================================
    # РАССЫЛКА
    # ==================================================================

    async def broadcast(self, message: ServerMessage) -> None:
        """
        Отправляет сообщение всем живым соединениям.

        Отвалившееся соединение просто снимается с учета: мир продолжает
        жить, даже если окно клиента закрылось посреди хода.
        """
        if not self._connections:
            return

        payload = message.model_dump(mode="json")
        broken: list[WebSocket] = []

        for connection in list(self._connections):
            try:
                await connection.send_json(payload)
            except Exception as error:
                main_logger.warning(f"[WS] Соединение потеряно: {error}")
                broken.append(connection)

        for connection in broken:
            self.disconnect(connection)

    async def send_personal(self, websocket: WebSocket, message: ServerMessage) -> None:
        """
        Отправляет сообщение одному соединению (приветствие, ответ на пинг).
        """
        await websocket.send_json(message.model_dump(mode="json"))
