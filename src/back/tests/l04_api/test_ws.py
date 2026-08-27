"""
Канал уведомлений: менеджер соединений, мост от шины и сам эндпоинт.
"""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.back.l01_domain.world.models.chronicle import RumorEntry
from src.back.l04_api.ws.dispatcher import EventDispatcher
from src.back.l04_api.ws.manager import ConnectionManager
from src.back.l04_api.ws.schemas import (
    CONNECTION_ESTABLISHED,
    CONNECTION_PONG,
    ServerMessage,
)
from src.back.utils.event.bus import EventBus
from src.back.utils.event.registry import GameEvents


# ==================================================================
# ЗАГЛУШКИ
# ==================================================================


class FakeManager(ConnectionManager):
    """Менеджер, который вместо отправки складывает сообщения в список."""

    def __init__(self) -> None:
        super().__init__()
        self.sent: list[ServerMessage] = []

    async def broadcast(self, message: ServerMessage) -> None:
        self.sent.append(message)


class BrokenSocket:
    """Соединение, разорвавшееся между тактами."""

    async def send_json(self, payload: dict) -> None:
        raise ConnectionResetError("окно клиента закрылось")


class RecordingSocket:
    """Живое соединение, запоминающее то, что ему прислали."""

    def __init__(self) -> None:
        self.received: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.received.append(payload)


# ==================================================================
# МЕНЕДЖЕР СОЕДИНЕНИЙ
# ==================================================================


async def test_broadcast_reaches_every_connection():
    manager = ConnectionManager()
    first, second = RecordingSocket(), RecordingSocket()
    manager._connections.update({first, second})  # type: ignore[arg-type]

    await manager.broadcast(ServerMessage(event="strategic.turn_completed"))

    assert first.received == second.received
    assert first.received[0]["event"] == "strategic.turn_completed"


async def test_broken_connection_is_dropped_and_others_survive():
    """Отвалившееся окно клиента не должно ронять рассылку остальным."""
    manager = ConnectionManager()
    alive, broken = RecordingSocket(), BrokenSocket()
    manager._connections.update({alive, broken})  # type: ignore[arg-type]

    await manager.broadcast(ServerMessage(event="tactical.turn_completed"))

    assert manager.connections_count == 1
    assert len(alive.received) == 1


async def test_broadcast_without_listeners_is_harmless():
    await ConnectionManager().broadcast(ServerMessage(event="strategic.turn_completed"))


# ==================================================================
# МОСТ ОТ ШИНЫ СОБЫТИЙ
# ==================================================================


@pytest.fixture
def bridge() -> tuple[EventBus, FakeManager, EventDispatcher]:
    bus = EventBus()
    manager = FakeManager()
    dispatcher = EventDispatcher(manager)
    dispatcher.register(bus)
    return bus, manager, dispatcher


async def test_event_reaches_the_socket(bridge: tuple[Any, FakeManager, Any]):
    bus, manager, _ = bridge

    await bus.publish(GameEvents.Strategic.TURN_COMPLETED, tick=7, encounters_count=2)

    assert len(manager.sent) == 1
    message = manager.sent[0]
    assert message.event == "strategic.turn_completed"
    assert message.data == {"tick": 7, "encounters_count": 2}


async def test_events_outside_the_list_do_not_leak(
    bridge: tuple[Any, FakeManager, Any]
):
    """
    Служебная механика раунда игроку не нужна: на нее никто не подписан.
    """
    bus, manager, _ = bridge

    await bus.publish(GameEvents.Tactical.PHASE_ADVANCED, phase="movement")

    assert manager.sent == []


async def test_domain_models_are_unpacked_for_json(
    bridge: tuple[Any, FakeManager, Any]
):
    bus, manager, _ = bridge
    rumor = RumorEntry(text="Говорят, в пустошах видели огни.", tick=12)

    await bus.publish(GameEvents.Chronicler.RUMOR_GENERATED, rumor=rumor)

    assert manager.sent[0].data["rumor"]["text"] == rumor.text


async def test_unserializable_field_is_skipped_not_fatal(
    bridge: tuple[Any, FakeManager, Any]
):
    """
    Живой объект в нагрузке события не должен рвать канал: поле молча
    выпадает, остальное доезжает.
    """
    bus, manager, _ = bridge

    await bus.publish(
        GameEvents.Tactical.BATTLE_STARTED,
        battle_id="battle-1",
        collector=object(),
    )

    assert manager.sent[0].data == {"battle_id": "battle-1"}


async def test_unregister_stops_the_stream(bridge: tuple[Any, FakeManager, Any]):
    bus, manager, dispatcher = bridge
    dispatcher.unregister(bus)

    await bus.publish(GameEvents.Strategic.TURN_COMPLETED, tick=1)

    assert manager.sent == []


# ==================================================================
# ЭНДПОИНТ
# ==================================================================


def test_client_is_greeted_and_answered_on_ping(client: TestClient):
    with client.websocket_connect("/ws") as socket:
        assert socket.receive_json()["event"] == CONNECTION_ESTABLISHED

        socket.send_json({"action": "ping"})
        assert socket.receive_json()["event"] == CONNECTION_PONG


def test_garbage_does_not_break_the_channel(client: TestClient):
    """Непонятное сообщение игнорируется: окно клиента не должно отваливаться."""
    with client.websocket_connect("/ws") as socket:
        socket.receive_json()

        socket.send_json({"мусор": True})
        socket.send_json({"action": "ping"})

        assert socket.receive_json()["event"] == CONNECTION_PONG


def test_connection_is_taken_off_the_books_after_disconnect(
    app: FastAPI, client: TestClient
):
    manager: ConnectionManager = app.state.ws_manager

    with client.websocket_connect("/ws") as socket:
        socket.receive_json()
        assert manager.connections_count == 1

    assert manager.connections_count == 0
