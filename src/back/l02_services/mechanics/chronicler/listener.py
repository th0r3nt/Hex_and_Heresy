"""
Pub/Sub подписчик. Слушает BattleEndedEvent и т.д.).

Единственное место модуля, знакомое с шиной событий: фасад летописца ничего
о ней не знает и вызывается напрямую.

Быстрые реакции (снять состав сторон, разнести числа раунда) выполняются
на месте - они трогают досье и обязаны успеть до следующего раунда. Медленные
(генерация летописи и слухов через языковую модель) уходят в фоновые задачи,
чтобы не задерживать ход игры.
"""

import asyncio
from typing import Any, Awaitable, Optional

from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.chronicler.facade import ChroniclerFacade
from src.back.utils.event.registry import GameEvents
from src.back.utils.logger import main_logger


class ChroniclerListener:
    """
    Подписывает летописца на события боя и глобального такта.
    """

    def __init__(
        self,
        facade: ChroniclerFacade,
        run_in_background: bool = True,
    ) -> None:
        self._facade = facade
        self._run_in_background = run_in_background
        self._world_state: Optional[WorldState] = None
        self._tasks: set[asyncio.Task[Any]] = set()

    # ==================================================================
    # ПРИВЯЗКА И ПОДПИСКИ
    # ==================================================================

    def bind_world_state(self, world_state: WorldState) -> None:
        """
        Привязывает активную партию. Вызывается composition root'ом после
        старта или загрузки игры: до этого момента WorldState не существует.
        """
        self._world_state = world_state

    def register(self, event_bus: EventBusProtocol) -> None:
        for event_name, handler in self._subscriptions():
            event_bus.subscribe(event_name, handler)

    def unregister(self, event_bus: EventBusProtocol) -> None:
        """
        Снимает подписки при выходе из партии в главное меню.
        """
        for event_name, handler in self._subscriptions():
            event_bus.unsubscribe(event_name, handler)

    def _subscriptions(self) -> list[tuple[Any, Any]]:
        return [
            (GameEvents.Tactical.BATTLE_STARTED, self.on_battle_started),
            (GameEvents.Tactical.TURN_COMPLETED, self.on_turn_completed),
            (GameEvents.Tactical.BATTLE_COMPLETED, self.on_battle_completed),
            (GameEvents.Tactical.HERO_SLAIN, self.on_hero_slain),
            (GameEvents.Strategic.TURN_COMPLETED, self.on_strategic_turn_completed),
            (GameEvents.GameFlow.GAME_OVER, self.on_game_over),
        ]

    # ==================================================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # ==================================================================

    def on_battle_started(
        self,
        battle_id: str,
        battle_state: Any,
        squads: dict,
        strategic_hex: Any = None,
        **_: Any,
    ) -> None:
        """
        Заводит досье боя по стартовому составу сторон.
        """
        
        world_state = self._require_world_state("начало боя")
        if world_state is None:
            return

        self._facade.on_battle_started(
            world_state=world_state,
            battle_state=battle_state,
            squads=squads,
            strategic_hex=strategic_hex,
        )

    def on_turn_completed(self, report: Any = None, **_: Any) -> None:
        """Разносит числа очередного раунда по досье."""
        if report is None:
            return
        self._facade.on_battle_turn(report)

    def on_battle_completed(self, report: Any = None, **_: Any) -> Optional[Awaitable[Any]]:
        """
        Закрывает бой и отправляет летопись в работу.

        Генерация текста уходит в фон: игрок должен увидеть итоги сражения
        сразу, а свиток дописывается и прилетает на фронт отдельно.
        """
        if report is None:
            return None
        world_state = self._require_world_state("завершение боя")
        if world_state is None:
            return None

        return self._run(self._facade.chronicle_battle(world_state, report))

    def on_hero_slain(
        self, battle_id: str, hero_name: str = "", **_: Any
    ) -> None:
        """Отмечает гибель героя в досье текущего боя."""
        if not hero_name:
            return
        self._facade.note_hero_slain(battle_id, hero_name)

    def on_strategic_turn_completed(self, **_: Any) -> Optional[Awaitable[Any]]:
        """
        Считает тишину и, если боев давно не было, роняет слух.
        """
        world_state = self._require_world_state("глобальный такт")
        if world_state is None:
            return None

        world_state.ticks_since_last_battle += 1
        return self._run(self._facade.speak_rumor(world_state))

    def on_game_over(self, result: Any = None, **_: Any) -> Optional[Awaitable[Any]]:
        """
        Дописывает последнюю главу хроники: партия закончилась.

        Как и летопись боя, текст уходит в фон - экран финала показывается
        игроку сразу, а ода или реквием прилетают на него отдельно.
        Финалы, объявленные не подсистемой победы (например, вручную из
        меню), приходят без вердикта и главы не получают.
        """
        if result is None:
            return None
        world_state = self._require_world_state("финал партии")
        if world_state is None:
            return None

        return self._run(self._facade.write_finale(world_state, result))

    # ==================================================================
    # ФОНОВЫЕ ЗАДАЧИ
    # ==================================================================

    async def wait_for_pending(self) -> None:
        """
        Дожидается фоновых генераций. Нужна тестам и остановке сервера:
        недописанная летопись не должна теряться при выходе.
        """
        if not self._tasks:
            return
        await asyncio.gather(*list(self._tasks), return_exceptions=True)

    def _run(self, coroutine: Awaitable[Any]) -> Optional[Awaitable[Any]]:
        """
        Запускает медленную работу летописца.

        В фоновом режиме возвращает задачу, в синхронном - саму корутину,
        которую шина событий дождется сама (так удобнее тестам и режимам без
        работающего цикла задач).
        """
        if not self._run_in_background:
            return coroutine

        task = asyncio.create_task(self._guard(coroutine))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return None

    async def _guard(self, coroutine: Awaitable[Any]) -> None:
        """
        Фоновая задача летописца не должна ронять процесс: летопись - это
        украшение партии, а не игровое правило.
        """
        try:
            await coroutine
        except Exception as error:
            main_logger.error(f"[Chronicler] Фоновая задача летописца упала: {error}")

    # ==================================================================
    # СЛУЖЕБНОЕ
    # ==================================================================

    def _require_world_state(self, occasion: str) -> Optional[WorldState]:
        if self._world_state is None:
            main_logger.warning(
                f"[Chronicler] Событие '{occasion}' пришло до привязки партии: "
                "вызовите bind_world_state()."
            )
        return self._world_state
