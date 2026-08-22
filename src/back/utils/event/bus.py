"""
Асинхронная локальная шина событий (Pub/Sub).
Позволяет реализовать слабую связанность между модулями.

Имплементирует EventBusProtocol из доменного слоя: ключом события служит
строковое значение перечислений из registry.py (напр. "strategic.turn_started").
"""

import asyncio
import inspect
from enum import Enum
from typing import Any, Awaitable, Callable, Union

from src.back.utils.logger import main_logger

# Публиковать можно как членом перечисления GameEvents, так и сырой строкой
EventName = Union[str, Enum]
EventHandler = Callable[..., Any]


def resolve_event_name(event: EventName) -> str:
    """
    Приводит событие к строковому ключу шины.

    Берется именно `value` перечисления, а не `name`: имена членов совпадают
    в разных доменах (StrategicEvents.TURN_STARTED и TacticalEvents.TURN_STARTED),
    и ключи разных событий склеились бы в один.
    """
    if isinstance(event, Enum):
        return event.value if isinstance(event.value, str) else str(event.value)
    return str(event)


def _handler_name(handler: EventHandler) -> str:
    """
    Человекочитаемое имя слушателя для логов.
    Функции и методы имеют __name__, а частичные применения и объекты-вызовы - нет.
    """
    return getattr(handler, "__name__", None) or repr(handler)


class EventBus:
    """
    Асинхронная локальная шина событий (Pub/Sub).
    Поддерживает синхронных и асинхронных слушателей.

    `publish` дожидается всех слушателей: игра пошаговая, и обработчик,
    дописывающий летопись или трогающий состояние мира, должен успеть
    отработать до конца такта. Медленные слушатели (напр. генерация текста через
    LLM) публикуются через `publish_background`.

    Исключение в одном слушателе логируется и не мешает остальным: событие
    информирует подписчиков, а не выполняет игровое правило, поэтому падение
    подписчика не должно ронять такт.
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[EventHandler]] = {}
        self._background_tasks: set[asyncio.Task[None]] = set()

    # ==================================================================
    # ПОДПИСКИ
    # ==================================================================

    def subscribe(self, event_name: EventName, handler: EventHandler) -> None:
        """
        Привязывает слушателя к событию. Повторная подписка того же обработчика
        игнорируется, иначе он был бы вызван дважды на одно событие.
        """
        key = resolve_event_name(event_name)
        handlers = self._listeners.setdefault(key, [])

        if handler in handlers:
            main_logger.warning(
                f"[EventBus] Слушатель '{_handler_name(handler)}' уже подписан на '{key}'."
            )
            return

        handlers.append(handler)
        main_logger.debug(f"[EventBus] Подписка: '{_handler_name(handler)}' -> '{key}'.")

    def unsubscribe(self, event_name: EventName, handler: EventHandler) -> None:
        """
        Снимает подписку. Отсутствие подписки не считается ошибкой.
        """
        key = resolve_event_name(event_name)
        handlers = self._listeners.get(key)
        if not handlers:
            return

        try:
            handlers.remove(handler)
        except ValueError:
            return

        if not handlers:
            del self._listeners[key]

    def clear(self) -> None:
        """
        Сбрасывает все подписки (используется при выходе из партии в меню).
        """
        self._listeners.clear()

    def listener_count(self, event_name: EventName) -> int:
        """
        Число подписчиков события - для диагностики и тестов.
        """
        return len(self._listeners.get(resolve_event_name(event_name), ()))

    # ==================================================================
    # ПУБЛИКАЦИЯ
    # ==================================================================

    async def publish(self, event_name: EventName, *args: Any, **kwargs: Any) -> None:
        """
        Публикует событие и дожидается завершения всех слушателей.
        """
        key = resolve_event_name(event_name)
        handlers = self._listeners.get(key)

        if not handlers:
            main_logger.debug(f"[EventBus] У события '{key}' нет подписчиков.")
            return

        await self._dispatch(key, list(handlers), args, kwargs)

    def publish_background(self, event_name: EventName, *args: Any, **kwargs: Any) -> None:
        """
        Публикует событие, не дожидаясь слушателей.

        Для долгих реакций, которые не должны задерживать ход: генерация
        летописи, слухов и прочие обращения к LLM. Завершения таких публикаций
        дожидается `stop()` при остановке приложения.
        """
        key = resolve_event_name(event_name)
        handlers = self._listeners.get(key)

        if not handlers:
            main_logger.debug(f"[EventBus] У события '{key}' нет подписчиков.")
            return

        task = asyncio.create_task(self._dispatch(key, list(handlers), args, kwargs))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def stop(self) -> None:
        """
        Дожидается завершения фоновых публикаций. Вызывается при остановке сервера.
        """
        if not self._background_tasks:
            return

        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

    # ==================================================================
    # СЛУЖЕБНОЕ
    # ==================================================================

    async def _dispatch(
        self,
        key: str,
        handlers: list[EventHandler],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        """
        Вызывает слушателей события.

        Синхронные слушатели отрабатывают сразу и по очереди - они трогают
        игровое состояние, которое живет в цикле событий, и уносить их в
        отдельный поток означало бы гонку за WorldState. Асинхронные
        собираются и выполняются параллельно.
        """
        pending: list[Awaitable[Any]] = []
        awaited_handlers: list[EventHandler] = []

        for handler in handlers:
            try:
                result = handler(*args, **kwargs)
            except Exception as e:
                self._log_handler_error(key, handler, e)
                continue

            if inspect.isawaitable(result):
                pending.append(result)
                awaited_handlers.append(handler)

        if not pending:
            return

        results = await asyncio.gather(*pending, return_exceptions=True)
        for handler, result in zip(awaited_handlers, results):
            if isinstance(result, BaseException):
                self._log_handler_error(key, handler, result)

    def _log_handler_error(
        self, key: str, handler: EventHandler, error: BaseException
    ) -> None:
        main_logger.error(
            f"[EventBus] Ошибка слушателя '{_handler_name(handler)}' события '{key}': {error}"
        )
