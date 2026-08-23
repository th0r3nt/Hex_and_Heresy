"""
Логика управления и взаимодействия с послами фракции.

Посол - физический юнит на глобальной карте: он идет ножками до чужой
цитадели, может вести с собой армию охраны и рискует головой на аудиенции
(см. game_mechanics/diplomacy.md).
"""

from typing import Optional

from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.exceptions import (
    AmbassadorUnavailableError,
    FactionCapitalUnknownError,
    SelfDiplomacyForbiddenError,
)
from src.back.l01_domain.factions.constants import (
    AMBASSADOR_SPEED_HEXES,
    AmbassadorStatus,
    NegotiationMode,
)
from src.back.l01_domain.factions.models.diplomacy.messengers import Ambassador
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.models.strategic import hex_line
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.event.registry import GameEvents


class AmbassadorService:
    """
    Ведет послов: отправка с маршрутом и охраной, пошаговое движение к чужой
    цитадели, начало аудиенции, казнь и возвращение домой.
    """

    def __init__(self, event_bus: Optional[EventBusProtocol] = None) -> None:
        self._event_bus = event_bus

    async def send(
        self,
        world_state: WorldState,
        faction_id: str,
        name: str,
        target_faction_id: str,
        traits: Optional[list[str]] = None,
        escort_army_id: Optional[str] = None,
        negotiation_mode: NegotiationMode = NegotiationMode.AUTOMATIC,
        directive: Optional[str] = None,
    ) -> Ambassador:
        """
        Отправляет посла к лорду другой фракции.
        Охрана (если выделена) идет вместе с послом и отдельного приказа
        на марш не получает - ее гекс синхронизируется с гексом посла.
        """
        if faction_id == target_faction_id:
            raise SelfDiplomacyForbiddenError(faction_id)

        sender = self._require_faction(world_state, faction_id)
        target = self._require_faction(world_state, target_faction_id)

        if sender.capital_hex is None:
            raise FactionCapitalUnknownError(sender.id)
        if target.capital_hex is None:
            raise FactionCapitalUnknownError(target.id)

        ambassador = Ambassador(
            faction_id=faction_id,
            name=name,
            traits=traits or [],
            status=AmbassadorStatus.TRAVELING,
            escort_army_id=escort_army_id,
            target_faction_id=target_faction_id,
            current_hex=sender.capital_hex,
            planned_path=hex_line(sender.capital_hex, target.capital_hex)[1:],
            negotiation_mode=negotiation_mode,
            directive=directive,
        )
        world_state.ambassadors.append(ambassador)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Diplomacy.AMBASSADOR_SENT,
                ambassador_id=ambassador.id,
                faction_id=faction_id,
                target_faction_id=target_faction_id,
                escort_army_id=escort_army_id,
            )

        return ambassador

    async def process_tick(self, world_state: WorldState) -> list[Ambassador]:
        """
        Продвигает всех послов в пути на один такт.
        Возвращает список тех, кто дошел до чужой цитадели в этом такте.
        """
        arrived: list[Ambassador] = []

        for ambassador in world_state.ambassadors:
            if ambassador.status != AmbassadorStatus.TRAVELING:
                continue

            self._advance(world_state, ambassador)

            if not ambassador.planned_path:
                ambassador.status = AmbassadorStatus.IN_AUDIENCE
                arrived.append(ambassador)
                if self._event_bus is not None:
                    await self._event_bus.publish(
                        GameEvents.Strategic.AMBASSADOR_ARRIVED,
                        ambassador_id=ambassador.id,
                        faction_id=ambassador.faction_id,
                        target_faction_id=ambassador.target_faction_id,
                    )

        return arrived

    async def execute_ambassador(
        self, world_state: WorldState, ambassador_id: str
    ) -> Ambassador:
        """
        Чужой лорд казнит посла: фракции автоматически переходят в состояние
        войны, а охрана остается в чужой цитадели - ее судьбу решает
        обычное обнаружение столкновений на такте.
        """
        
        ambassador = self._require_ambassador(world_state, ambassador_id)
        if ambassador.status != AmbassadorStatus.IN_AUDIENCE:
            raise AmbassadorUnavailableError(ambassador_id, ambassador.status.value)

        ambassador.status = AmbassadorStatus.EXECUTED
        world_state.ambassadors.remove(ambassador)

        target_faction_id = ambassador.target_faction_id or ""
        relation = world_state.get_or_create_relation(
            ambassador.faction_id, target_faction_id
        )
        relation.declare_war()

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Diplomacy.AMBASSADOR_EXECUTED,
                ambassador_id=ambassador.id,
                faction_id=ambassador.faction_id,
                executed_by_faction_id=target_faction_id,
                escort_army_id=ambassador.escort_army_id,
            )
            await self._event_bus.publish(
                GameEvents.Diplomacy.WAR_DECLARED,
                faction_a_id=ambassador.faction_id,
                faction_b_id=target_faction_id,
                reason="ambassador_executed",
            )

        return ambassador

    async def send_home(self, world_state: WorldState, ambassador_id: str) -> Ambassador:
        """
        Аудиенция закончена миром: посол отзывается домой и покидает карту.
        """
        ambassador = self._require_ambassador(world_state, ambassador_id)
        ambassador.status = AmbassadorStatus.RETURNED
        world_state.ambassadors.remove(ambassador)
        return ambassador

    # ==================================================================
    # ВНУТРЕННЯЯ ЛОГИКА
    # ==================================================================

    def _advance(self, world_state: WorldState, ambassador: Ambassador) -> None:
        """
        Проводит посла по маршруту на один такт и подтягивает за ним охрану.
        """
        steps = min(self._speed(world_state, ambassador), len(ambassador.planned_path))
        for _ in range(steps):
            ambassador.current_hex = ambassador.planned_path.pop(0)

        escort = self._escort_army(world_state, ambassador)
        if escort is not None and ambassador.current_hex is not None:
            escort.current_hex = ambassador.current_hex

    def _speed(self, world_state: WorldState, ambassador: Ambassador) -> int:
        """
        Посол под охраной идет со скоростью своей армии, одиночка - пешком.
        """
        escort = self._escort_army(world_state, ambassador)
        if escort is not None:
            return escort.max_movement_range
        return AMBASSADOR_SPEED_HEXES

    def _escort_army(
        self, world_state: WorldState, ambassador: Ambassador
    ) -> Optional[StrategicArmy]:
        if ambassador.escort_army_id is None:
            return None
        return world_state.get_army(ambassador.escort_army_id)

    def _require_faction(self, world_state: WorldState, faction_id: str) -> Faction:
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise ValueError(f"Фракция {faction_id} не найдена")
        return faction

    def _require_ambassador(
        self, world_state: WorldState, ambassador_id: str
    ) -> Ambassador:
        for ambassador in world_state.ambassadors:
            if ambassador.id == ambassador_id:
                return ambassador
        raise AmbassadorUnavailableError(ambassador_id, "not_found")
