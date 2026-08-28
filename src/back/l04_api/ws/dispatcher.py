"""
Мост между шиной событий и сокетом.

Подписывается на игровые события и пересылает их клиенту готовыми
конвертами, чтобы интерфейсу не приходилось опрашивать сервер по HTTP.

Пересылается не все подряд, а именно то, что видно игроку: список событий
задан явно. Так канал не забивается служебной механикой вроде фаз раунда,
а добавление нового события в реестр не начинает молча течь на фронт.
"""

from enum import Enum
from functools import partial
from typing import Any

from pydantic import BaseModel

from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l04_api.ws.manager import ConnectionManager
from src.back.l04_api.ws.schemas import ServerMessage
from src.back.utils.event.bus import resolve_event_name
from src.back.utils.event.registry import GameEvents
from src.back.utils.logger import main_logger

# ====================================================
# Что именно видит игрок
# ====================================================

BROADCAST_EVENTS: tuple[Enum, ...] = (
    # Режимы игры
    GameEvents.GameFlow.STATE_CHANGED,
    GameEvents.GameFlow.GAME_SAVED,
    GameEvents.GameFlow.GAME_LOADED,
    GameEvents.GameFlow.GAME_OVER,
    # Глобальная карта
    GameEvents.Strategic.TURN_COMPLETED,
    GameEvents.Strategic.GREY_HOURS_STARTED,
    GameEvents.Strategic.NEON_HOURS_STARTED,
    GameEvents.Strategic.ENCOUNTER_DETECTED,
    GameEvents.Strategic.DISPATCH_DELIVERED,
    GameEvents.Strategic.DISPATCH_INTERCEPTED,
    GameEvents.Strategic.AMBASSADOR_ARRIVED,
    GameEvents.Strategic.HERO_RECOVERED,
    GameEvents.Strategic.SQUAD_STATIONED,
    GameEvents.Strategic.SQUAD_UNSTATIONED,
    GameEvents.Strategic.MILITIA_CAPACITY_SYNCED,
    # Экономика
    GameEvents.Economy.BUILDING_COMPLETED,
    GameEvents.Economy.EXPEDITION_RETURNED,
    GameEvents.Economy.EXPEDITION_LOST,
    GameEvents.Economy.FAMINE_OCCURRED,
    GameEvents.Economy.SQUAD_DESERTED,
    GameEvents.Economy.BORDER_TOWN_FOUNDED,
    GameEvents.Economy.BORDER_TOWN_UPGRADED,
    GameEvents.Economy.BORDER_TOWN_LAND_CLAIMED,
    # Тактический бой
    GameEvents.Tactical.BATTLE_STARTED,
    GameEvents.Tactical.TURN_COMPLETED,
    GameEvents.Tactical.SQUAD_PANICKED,
    GameEvents.Tactical.HERO_WOUNDED,
    GameEvents.Tactical.HERO_SLAIN,
    GameEvents.Tactical.BATTLE_COMPLETED,
    # Дипломатия
    GameEvents.Diplomacy.WAR_DECLARED,
    GameEvents.Diplomacy.PEACE_SIGNED,
    GameEvents.Diplomacy.PACT_FORMED,
    GameEvents.Diplomacy.PACT_BROKEN,
    GameEvents.Diplomacy.TRIBUTE_DEMANDED,
    GameEvents.Diplomacy.AMBASSADOR_EXECUTED,
    # Летописец: тексты дописываются в фоне и прилетают отдельно от хода
    GameEvents.Chronicler.BATTLE_RECORDED,
    GameEvents.Chronicler.FALLEN_RECORDED,
    GameEvents.Chronicler.RUMOR_GENERATED,
    GameEvents.Chronicler.SQUAD_PROMOTED,
    # Оружейник и мастер игры
    GameEvents.Gunsmith.BLUEPRINT_DRAFTED,
    GameEvents.Gunsmith.BLUEPRINT_APPROVED,
    GameEvents.GameMaster.GLOBAL_EVENT_SPAWNED,
    GameEvents.GameMaster.CHARACTER_CREATED,
    # Советник: непрошеный совет рождается между ходами и приходит сам
    GameEvents.Advisor.PROPOSAL_OFFERED,
    GameEvents.Advisor.ACTION_EXECUTED,
)


class _Unserializable:
    """Маркер значения, которому нет места в JSON."""


_UNSERIALIZABLE = _Unserializable()


class EventDispatcher:
    """
    Переводит события шины в сообщения сокета.
    """

    def __init__(
        self,
        manager: ConnectionManager,
        events: tuple[Enum, ...] = BROADCAST_EVENTS,
    ) -> None:
        self._manager = manager
        self._events = events
        # Обработчик на каждое событие свой (в нем зашито имя), поэтому его
        # нужно запомнить: отписаться можно только тем же объектом
        self._handlers: dict[str, Any] = {}

    # ==================================================================
    # ПОДПИСКИ
    # ==================================================================

    def register(self, event_bus: EventBusProtocol) -> None:
        """
        Подписывает мост на игровые события. Вызывается при старте приложения.
        """
        for event in self._events:
            key = resolve_event_name(event)
            handler = self._handlers.setdefault(key, partial(self._forward, key))
            event_bus.subscribe(event, handler)

    def unregister(self, event_bus: EventBusProtocol) -> None:
        """
        Снимает подписки при остановке приложения.
        """
        for key, handler in self._handlers.items():
            event_bus.unsubscribe(key, handler)
        self._handlers.clear()

    # ==================================================================
    # ПЕРЕСЫЛКА
    # ==================================================================

    async def _forward(self, event_key: str, *args: Any, **kwargs: Any) -> None:
        """
        Отправляет событие клиенту.

        Позиционные аргументы игнорируются: сервисы публикуют события
        именованными полями, и только они превращаются в тело сообщения.
        """
        await self._manager.broadcast(
            ServerMessage(event=event_key, data=self._to_payload(event_key, kwargs))
        )

    def _to_payload(self, event_key: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        Приводит нагрузку события к виду, который переживет JSON.

        Поле, которое сериализовать нечем (живой объект мира, отряд, ссылка
        на сервис), в сокет не едет: интерфейсу оно все равно бесполезно.
        """
        payload: dict[str, Any] = {}

        for name, value in kwargs.items():
            converted = self._to_jsonable(value)
            if converted is _UNSERIALIZABLE:
                main_logger.debug(
                    f"[WS] Поле '{name}' события '{event_key}' не сериализуется "
                    "и в сокет не поехало."
                )
                continue
            payload[name] = converted

        return payload

    def _to_jsonable(self, value: Any) -> Any:
        """
        Разворачивает значение в примитивы. Возвращает маркер, если не вышло.
        """
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, (list, tuple, set)):
            items = [self._to_jsonable(item) for item in value]
            return [item for item in items if item is not _UNSERIALIZABLE]
        if isinstance(value, dict):
            converted = {
                str(key): self._to_jsonable(item) for key, item in value.items()
            }
            return {
                key: item
                for key, item in converted.items()
                if item is not _UNSERIALIZABLE
            }
        return _UNSERIALIZABLE
