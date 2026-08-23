"""
Логика управления и создания писем-депеш к чужим фракциям.

Гонец - не абстрактный таймер, а юнит на глобальной карте: у депеши есть
маршрут по гексам, цена найма гонца и шанс быть перехваченной чужой армией
на каждом пройденном гексе (см. game_mechanics/diplomacy.md).
"""

import math
from random import Random
from typing import Optional

from src.back.l01_domain.exceptions import (
    FactionCapitalUnknownError,
    SelfDiplomacyForbiddenError,
)
from src.back.l01_domain.factions.constants import (
    DISPATCH_BASE_COST_GOLD,
    DISPATCH_COST_GOLD_PER_HEX,
    DISPATCH_COURIER_SPEED_HEXES,
    DISPATCH_INTERCEPT_CHANCE,
    ResourceType,
)
from src.back.l01_domain.factions.models.diplomacy.messengers import Dispatch
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.models.strategic import HexCoordinates, hex_line
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.event.registry import GameEvents


class DispatchService:
    """
    Ведет письма-депеши: считает маршрут и цену при отправке, продвигает
    гонца по гексам каждый такт и бросает проверку перехвата.
    """

    def __init__(
        self,
        event_bus: Optional[EventBusProtocol] = None,
        rng: Optional[Random] = None,
    ) -> None:
        self._event_bus = event_bus
        self._rng = rng or Random()

    async def send(
        self,
        world_state: WorldState,
        sender_faction_id: str,
        recipient_faction_id: str,
        message_text: str,
    ) -> Dispatch:
        """
        Нанимает гонца и отправляет письмо в цитадель другой фракции.
        Золото списывается сразу, при нехватке казны - InsufficientResourcesError.
        """
        if sender_faction_id == recipient_faction_id:
            raise SelfDiplomacyForbiddenError(sender_faction_id)

        sender = self._require_faction(world_state, sender_faction_id)
        recipient = self._require_faction(world_state, recipient_faction_id)

        route = self._build_route(sender, recipient)
        cost_gold = DISPATCH_BASE_COST_GOLD + DISPATCH_COST_GOLD_PER_HEX * len(route)
        sender.spend(ResourceType.GOLD, cost_gold)

        travel_ticks = self._ticks_for(len(route))
        dispatch = Dispatch(
            sender_faction_id=sender_faction_id,
            recipient_faction_id=recipient_faction_id,
            message_text=message_text,
            cost_gold=cost_gold,
            route=route,
            total_travel_ticks=travel_ticks,
            travel_ticks_remaining=travel_ticks,
        )
        world_state.dispatches.append(dispatch)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Diplomacy.DISPATCH_SENT,
                dispatch_id=dispatch.id,
                sender_faction_id=sender_faction_id,
                recipient_faction_id=recipient_faction_id,
                travel_ticks=travel_ticks,
                cost_gold=cost_gold,
            )

        return dispatch

    async def process_tick(
        self, world_state: WorldState
    ) -> tuple[list[Dispatch], list[Dispatch]]:
        """
        Продвигает всех гонцов на один такт.
        Возвращает кортеж (доставленные, перехваченные) - обе группы
        уходят из активного реестра мира.
        """
        delivered: list[Dispatch] = []
        intercepted: list[Dispatch] = []
        still_traveling: list[Dispatch] = []

        for dispatch in world_state.dispatches:
            await self._advance(world_state, dispatch)

            if dispatch.is_intercepted:
                intercepted.append(dispatch)
                world_state.add_intercepted_dispatch(
                    dispatch.intercepted_by_faction_id or "", dispatch
                )
                if self._event_bus is not None:
                    await self._event_bus.publish(
                        GameEvents.Strategic.DISPATCH_INTERCEPTED,
                        dispatch_id=dispatch.id,
                        sender_faction_id=dispatch.sender_faction_id,
                        recipient_faction_id=dispatch.recipient_faction_id,
                        intercepted_by_faction_id=dispatch.intercepted_by_faction_id,
                    )
            elif not dispatch.route:
                delivered.append(dispatch)
                if self._event_bus is not None:
                    await self._event_bus.publish(
                        GameEvents.Strategic.DISPATCH_DELIVERED,
                        dispatch_id=dispatch.id,
                        sender_faction_id=dispatch.sender_faction_id,
                        recipient_faction_id=dispatch.recipient_faction_id,
                    )
            else:
                still_traveling.append(dispatch)

        world_state.dispatches = still_traveling
        return delivered, intercepted

    # ==================================================================
    # ВНУТРЕННЯЯ ЛОГИКА
    # ==================================================================

    async def _advance(self, world_state: WorldState, dispatch: Dispatch) -> None:
        """
        Проводит гонца по гексам маршрута за один такт, проверяя каждый
        пройденный гекс на перехват. Перехват обрывает путь.
        """
        steps = min(DISPATCH_COURIER_SPEED_HEXES, len(dispatch.route))

        for _ in range(steps):
            hex_coord = dispatch.route.pop(0)
            interceptor_id = self._roll_interception(world_state, dispatch, hex_coord)
            if interceptor_id is not None:
                dispatch.is_intercepted = True
                dispatch.intercepted_by_faction_id = interceptor_id
                dispatch.travel_ticks_remaining = 0
                return

        dispatch.travel_ticks_remaining = self._ticks_for(len(dispatch.route))

    def _roll_interception(
        self, world_state: WorldState, dispatch: Dispatch, hex_coord: HexCoordinates
    ) -> Optional[str]:
        """
        Возвращает id фракции, перехватившей письмо на этом гексе, или None.
        Каждая чужая армия на гексе получает свой бросок.
        """
        own_factions = (dispatch.sender_faction_id, dispatch.recipient_faction_id)

        for army in world_state.get_armies_at_hex(hex_coord):
            if army.faction_id in own_factions:
                continue
            if self._rng.random() < DISPATCH_INTERCEPT_CHANCE:
                return army.faction_id

        return None

    def _build_route(self, sender: Faction, recipient: Faction) -> list[HexCoordinates]:
        """
        Прокладывает путь гонца от цитадели отправителя к цитадели получателя.
        Гекс отправления в маршрут не входит - на своей земле гонца не ловят.
        """
        if sender.capital_hex is None:
            raise FactionCapitalUnknownError(sender.id)
        if recipient.capital_hex is None:
            raise FactionCapitalUnknownError(recipient.id)

        return hex_line(sender.capital_hex, recipient.capital_hex)[1:]

    def _ticks_for(self, hexes_left: int) -> int:
        """Сколько тактов гонцу осталось скакать."""
        return math.ceil(hexes_left / DISPATCH_COURIER_SPEED_HEXES)

    def _require_faction(self, world_state: WorldState, faction_id: str) -> Faction:
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise ValueError(f"Фракция {faction_id} не найдена")
        return faction
