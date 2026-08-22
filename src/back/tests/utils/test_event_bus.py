"""
Тесты асинхронной локальной шины событий.
"""

import asyncio

from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.utils.event.bus import EventBus, resolve_event_name
from src.back.utils.event.registry import GameEvents, StrategicEvents, TacticalEvents


class TestEventNameResolution:
    def test_enum_resolves_to_its_value(self):
        assert resolve_event_name(GameEvents.GameFlow.GAME_SAVED) == "gameflow.game_saved"

    def test_string_key_resolves_to_itself(self):
        assert resolve_event_name("gameflow.game_saved") == "gameflow.game_saved"

    def test_same_named_members_of_different_domains_do_not_collide(self):
        """У стратегического и тактического ходов совпадают имена членов, но не события."""
        assert StrategicEvents.TURN_STARTED.name == TacticalEvents.TURN_STARTED.name
        assert resolve_event_name(StrategicEvents.TURN_STARTED) != resolve_event_name(
            TacticalEvents.TURN_STARTED
        )

    async def test_domains_deliver_independently(self):
        bus = EventBus()
        received: list[str] = []

        bus.subscribe(StrategicEvents.TURN_STARTED, lambda: received.append("strategic"))
        bus.subscribe(TacticalEvents.TURN_STARTED, lambda: received.append("tactical"))

        await bus.publish(TacticalEvents.TURN_STARTED)

        assert received == ["tactical"]


class TestSubscriptions:
    async def test_async_handler_receives_payload(self):
        bus = EventBus()
        received: list[dict] = []

        async def listener(**kwargs):
            received.append(kwargs)

        bus.subscribe(GameEvents.GameFlow.GAME_SAVED, listener)
        await bus.publish(GameEvents.GameFlow.GAME_SAVED, save_id="s1", total_ticks=7)

        assert received == [{"save_id": "s1", "total_ticks": 7}]

    async def test_sync_handler_is_supported(self):
        bus = EventBus()
        received: list[tuple] = []

        bus.subscribe(GameEvents.GameFlow.GAME_LOADED, lambda *a: received.append(a))
        await bus.publish(GameEvents.GameFlow.GAME_LOADED, "s1")

        assert received == [("s1",)]

    async def test_enum_and_string_keys_are_interchangeable(self):
        bus = EventBus()
        calls: list[int] = []

        bus.subscribe(GameEvents.GameFlow.GAME_SAVED, lambda: calls.append(1))
        await bus.publish("gameflow.game_saved")

        assert calls == [1]

    async def test_duplicate_subscription_fires_once(self):
        bus = EventBus()
        calls: list[int] = []

        def listener():
            calls.append(1)

        bus.subscribe(GameEvents.GameFlow.GAME_SAVED, listener)
        bus.subscribe(GameEvents.GameFlow.GAME_SAVED, listener)

        await bus.publish(GameEvents.GameFlow.GAME_SAVED)

        assert bus.listener_count(GameEvents.GameFlow.GAME_SAVED) == 1
        assert calls == [1]

    async def test_unsubscribe_stops_delivery(self):
        bus = EventBus()
        calls: list[int] = []

        def listener():
            calls.append(1)

        bus.subscribe(GameEvents.GameFlow.GAME_SAVED, listener)
        bus.unsubscribe(GameEvents.GameFlow.GAME_SAVED, listener)
        await bus.publish(GameEvents.GameFlow.GAME_SAVED)

        assert calls == []
        assert bus.listener_count(GameEvents.GameFlow.GAME_SAVED) == 0

    def test_unsubscribe_of_unknown_handler_is_silent(self):
        bus = EventBus()

        bus.unsubscribe(GameEvents.GameFlow.GAME_SAVED, lambda: None)

    async def test_publish_without_listeners_is_noop(self):
        await EventBus().publish(GameEvents.GameFlow.GAME_OVER)

    async def test_clear_drops_all_subscriptions(self):
        bus = EventBus()
        calls: list[int] = []

        bus.subscribe(GameEvents.GameFlow.GAME_SAVED, lambda: calls.append(1))
        bus.clear()
        await bus.publish(GameEvents.GameFlow.GAME_SAVED)

        assert calls == []


class TestDispatchGuarantees:
    async def test_publish_awaits_handlers(self):
        """Ход не должен уехать вперед подписчика, дописывающего состояние."""
        bus = EventBus()
        finished: list[str] = []

        async def slow_listener():
            await asyncio.sleep(0.01)
            finished.append("done")

        bus.subscribe(StrategicEvents.TURN_COMPLETED, slow_listener)
        await bus.publish(StrategicEvents.TURN_COMPLETED)

        assert finished == ["done"]

    async def test_failing_handler_does_not_block_others(self):
        bus = EventBus()
        survived: list[str] = []

        def broken_sync():
            raise RuntimeError("синхронный слушатель упал")

        async def broken_async():
            raise RuntimeError("асинхронный слушатель упал")

        async def healthy():
            survived.append("ok")

        bus.subscribe(StrategicEvents.TURN_STARTED, broken_sync)
        bus.subscribe(StrategicEvents.TURN_STARTED, broken_async)
        bus.subscribe(StrategicEvents.TURN_STARTED, healthy)

        await bus.publish(StrategicEvents.TURN_STARTED)

        assert survived == ["ok"]

    async def test_unsubscribe_during_dispatch_is_safe(self):
        """Слушатель вправе отписаться прямо в обработчике - список правится по копии."""
        bus = EventBus()
        calls: list[str] = []

        def once():
            calls.append("once")
            bus.unsubscribe(StrategicEvents.TURN_STARTED, once)

        bus.subscribe(StrategicEvents.TURN_STARTED, once)
        await bus.publish(StrategicEvents.TURN_STARTED)
        await bus.publish(StrategicEvents.TURN_STARTED)

        assert calls == ["once"]


class TestBackgroundPublishing:
    async def test_background_publish_does_not_wait(self):
        bus = EventBus()
        released = asyncio.Event()
        finished: list[str] = []

        async def slow_listener():
            await released.wait()
            finished.append("done")

        bus.subscribe(GameEvents.Chronicler.BATTLE_RECORDED, slow_listener)
        bus.publish_background(GameEvents.Chronicler.BATTLE_RECORDED)

        assert finished == []

        released.set()
        await bus.stop()

        assert finished == ["done"]

    async def test_stop_without_background_tasks_is_noop(self):
        await EventBus().stop()


class TestProtocolCompliance:
    def test_bus_satisfies_domain_protocol(self):
        assert isinstance(EventBus(), EventBusProtocol)
