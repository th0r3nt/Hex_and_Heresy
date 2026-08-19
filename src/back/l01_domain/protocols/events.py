"""
Протокол асинхронной шины событий.
"""

from typing import Any, Callable, Coroutine, Protocol, runtime_checkable


@runtime_checkable
class EventBusProtocol(Protocol):
    """
    Контракт асинхронной шины событий для слабой связанности модулей.
    """

    def subscribe(
        self, event_name: str, handler: Callable[..., Coroutine[Any, Any, None] | Any]
    ) -> None:
        ...

    def unsubscribe(
        self, event_name: str, handler: Callable[..., Coroutine[Any, Any, None] | Any]
    ) -> None:
        ...

    async def publish(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        ...