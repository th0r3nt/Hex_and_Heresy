"""
Главный фасад игрового потока для внешних слоев и API.
"""

from typing import Optional

from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.models.gameflow import (
    CombatResolutionPayload,
    CombatTransitionPayload,
    DiplomacyTransitionPayload,
    GameOverPayload,
    GlobalEventTransitionPayload,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.gameflow.fsm import GameFlowFSM
from src.back.l02_services.gameflow.guards import (
    ActionForbiddenInCurrentStateError,
    WorldStateNotBoundError,
    is_building_action_allowed,
    is_diplomacy_action_allowed,
    is_recruitment_action_allowed,
    is_saving_allowed,
)
from src.back.l02_services.gameflow.states import GameFlowTrigger, GameState


class GameFlowFacade:
    """
    Фасад оркестрации игровых режимов и проверки прав на выполнение действий.
    Предоставляет методы высокого уровня для смены экранов и фаз игры.
    """

    def __init__(
        self,
        fsm: Optional[GameFlowFSM] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._fsm = fsm or GameFlowFSM(event_bus=event_bus)
        self._world_state: Optional[WorldState] = None

    @property
    def current_state(self) -> GameState:
        """
        Текущий режим игры.
        """
        return self._fsm.current_state

    @property
    def world_state(self) -> Optional[WorldState]:
        """
        Мир активной партии или None, если партия не начата.
        """
        return self._world_state

    @property
    def active_battle_state(self) -> Optional[TacticalBattleState]:
        """
        Состояние идущего тактического боя.

        Живет в контексте перехода конечного автомата: тем же объектом, что
        ушел в enter_tactical_combat, - поэтому раунды продолжают считаться
        по нему же, а не по копии.
        """
        payload = self._fsm.current_payload
        if isinstance(payload, CombatTransitionPayload):
            return payload.battle_state
        return None

    # ==================================================================
    # ПРИВЯЗКА АКТИВНОЙ ПАРТИИ
    # ==================================================================

    def bind_world_state(self, world_state: WorldState) -> None:
        """
        Привязывает WorldState активной партии к фасаду. Вызывается composition
        root'ом сразу после start_new_game()/load_game() - до этого момента
        WorldState ещё не существует, поэтому привязка не идёт через конструктор.
        """
        self._world_state = world_state

    def unbind_world_state(self) -> None:
        """
        Отвязывает WorldState (например, при выходе в главное меню).
        """
        self._world_state = None

    # ==================================================================
    # ПРОВЕРКИ ДОПУСТИМОСТИ ДЕЙСТВИЙ
    # ==================================================================

    def assert_can_perform_diplomacy(self) -> None:
        """
        Проверяет право на дипломатические действия в текущем режиме.
        """
        if not is_diplomacy_action_allowed(self.current_state):
            raise ActionForbiddenInCurrentStateError("дипломатия", self.current_state)

    def assert_can_build(self) -> None:
        """
        Проверяет право на строительные работы.
        """
        if not is_building_action_allowed(self.current_state):
            raise ActionForbiddenInCurrentStateError("строительство", self.current_state)

    def assert_can_recruit(self) -> None:
        """
        Проверяет право на найм войск.
        """
        if not is_recruitment_action_allowed(self.current_state):
            raise ActionForbiddenInCurrentStateError("найм войск", self.current_state)

    def assert_can_save(self) -> None:
        """
        Проверяет возможность сохранения игры.
        """
        if not is_saving_allowed(self.current_state):
            raise ActionForbiddenInCurrentStateError("сохранение игры", self.current_state)

    # ==================================================================
    # УПРАВЛЕНИЕ РЕЖИМАМИ И СОСТОЯНИЯМИ
    # ==================================================================

    async def start_new_game(self) -> GameState:
        """
        Начинает новую партию и переводит игру на глобальную карту.
        """
        return await self._fsm.trigger(GameFlowTrigger.START_NEW_GAME)

    async def load_game(self) -> GameState:
        """
        Загружает сохранение и переходит на глобальную карту.
        """
        return await self._fsm.trigger(GameFlowTrigger.LOAD_SAVED_GAME)

    async def enter_tactical_combat(
        self,
        hex_coords: HexCoordinates,
        attacker_faction_id: str,
        defender_faction_id: str,
        battle_state: TacticalBattleState,
    ) -> GameState:
        """
        Инициирует тактический бой между двумя фракциями.
        При успешном переходе блокирует армии обеих сторон, стоящие на гексе боя,
        от параллельной работы/движения на стратегическом такте.

        Гарнизон гекса тоже замораживается: пока идет штурм, игрок не может
        ни завести за стены подкрепление, ни вывести оттуда защитников.
        """

        if self._world_state is None:
            raise WorldStateNotBoundError("enter_tactical_combat")

        payload = CombatTransitionPayload(
            hex_coordinates=hex_coords,
            attacker_faction_id=attacker_faction_id,
            defender_faction_id=defender_faction_id,
            battle_state=battle_state,
        )
        new_state = await self._fsm.trigger(GameFlowTrigger.ENGAGE_COMBAT, payload=payload)

        engaged_armies = [
            army
            for army in self._world_state.get_armies_at_hex(hex_coords)
            if army.faction_id in (attacker_faction_id, defender_faction_id)
        ]
        self._world_state.lock_armies_for_battle(
            battle_id=battle_state.id,
            army_ids=[army.id for army in engaged_armies],
        )

        garrison = self._world_state.get_garrison_at(hex_coords)
        if garrison is not None:
            self._world_state.lock_garrisons_for_battle(
                battle_id=battle_state.id, zone_ids=[garrison.zone_id]
            )

        return new_state

    async def finish_tactical_combat(
        self,
        battle_id: str,
        victor_faction_id: Optional[str] = None,
        is_base_destroyed: bool = False,
    ) -> GameState:
        """
        Завершает тактический бой, возвращает игру на глобальную карту
        и снимает лок с армий и гарнизона, задействованных в этом бою.
        """

        if self._world_state is None:
            raise WorldStateNotBoundError("finish_tactical_combat")

        payload = CombatResolutionPayload(
            battle_id=battle_id,
            victor_faction_id=victor_faction_id,
            is_base_destroyed=is_base_destroyed,
        )
        new_state = await self._fsm.trigger(GameFlowTrigger.RESOLVE_COMBAT, payload=payload)

        self._world_state.release_armies_from_battle(battle_id)
        self._world_state.release_garrisons_from_battle(battle_id)

        return new_state

    async def open_diplomatic_session(
        self,
        initiator_faction_id: str,
        target_faction_id: str,
        ambassador_id: Optional[str] = None,
    ) -> GameState:
        """
        Открывает окно дипломатической аудиенции.
        """
        payload = DiplomacyTransitionPayload(
            initiator_faction_id=initiator_faction_id,
            target_faction_id=target_faction_id,
            ambassador_id=ambassador_id,
        )
        return await self._fsm.trigger(GameFlowTrigger.OPEN_AUDIENCE, payload=payload)

    async def close_diplomatic_session(self) -> GameState:
        """
        Закрывает окно дипломатии и возвращает в режим карты.
        """
        return await self._fsm.trigger(GameFlowTrigger.CLOSE_AUDIENCE)

    async def show_global_event(self, event: GlobalEvent) -> GameState:
        """
        Отображает модальное окно глобального кризиса или события мастера игры.
        """
        payload = GlobalEventTransitionPayload(event=event)
        return await self._fsm.trigger(GameFlowTrigger.TRIGGER_GLOBAL_EVENT, payload=payload)

    async def resolve_global_event(self) -> GameState:
        """
        Закрывает окно события после принятия игроком решения.
        """
        return await self._fsm.trigger(GameFlowTrigger.RESOLVE_GLOBAL_EVENT)

    async def pause_game(self) -> GameState:
        """
        Ставит игру на паузу с сохранением точки возврата.
        """
        return await self._fsm.trigger(GameFlowTrigger.PAUSE_GAME)

    async def resume_game(self) -> GameState:
        """
        Снимает игру с паузы и возвращает в предыдущий режим.
        """
        return await self._fsm.trigger(GameFlowTrigger.RESUME_GAME)

    async def open_settings(self) -> GameState:
        """
        Открывает экран настроек.
        """
        return await self._fsm.trigger(GameFlowTrigger.OPEN_SETTINGS)

    async def close_settings(self) -> GameState:
        """
        Закрывает экран настроек и возвращает в предыдущий режим.
        """
        return await self._fsm.trigger(GameFlowTrigger.CLOSE_SETTINGS)

    async def open_credits(self) -> GameState:
        """
        Открывает экран авторов из главного меню.
        """
        return await self._fsm.trigger(GameFlowTrigger.OPEN_CREDITS)

    async def close_credits(self) -> GameState:
        """
        Закрывает экран авторов и возвращает в главное меню.
        """
        return await self._fsm.trigger(GameFlowTrigger.CLOSE_CREDITS)

    async def trigger_game_over(
        self, is_player_victorious: bool, reason: str, total_ticks: int = 0
    ) -> GameState:
        """
        Фиксирует окончание партии (победу или поражение).
        """
        payload = GameOverPayload(
            is_player_victorious=is_player_victorious,
            reason=reason,
            total_ticks_survived=total_ticks,
        )
        return await self._fsm.trigger(GameFlowTrigger.DECLARE_GAME_OVER, payload=payload)

    async def quit_to_main_menu(self) -> GameState:
        """
        Выходит в главное меню и отвязывает WorldState завершённой сессии.
        """
        new_state = await self._fsm.trigger(GameFlowTrigger.QUIT_TO_MAIN_MENU)
        self.unbind_world_state()
        return new_state
