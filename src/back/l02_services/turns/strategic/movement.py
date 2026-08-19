"""
Сервис перемещения армий, проверки засад, боевых столкновений
и дипломатической логистики (депеши, послы).
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.army.constants import StrategicMovementPace
from src.back.l01_domain.factions.constants import AmbassadorStatus, DiplomaticStance
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState


# TODO: в l1_domain?
class EncounterEvent(BaseModel):
    """
    Событие боевого столкновения двух армий на гексе.
    """

    hex_coordinates: HexCoordinates = Field(...)
    faction_a_id: str = Field(...)
    faction_b_id: str = Field(...)
    army_a_id: str = Field(...)
    army_b_id: str = Field(...)
    is_ambush: bool = Field(default=False)
    ambusher_army_id: Optional[str] = Field(default=None)


# TODO: в l1_domain?
class MovementStepReport(BaseModel):
    """
    Отчет о перемещениях, столкновениях и доставке дипломатии.
    """

    moved_army_ids: list[str] = Field(default_factory=list)
    encounters: list[EncounterEvent] = Field(default_factory=list)
    delivered_dispatch_ids: list[str] = Field(default_factory=list)
    intercepted_dispatch_ids: list[str] = Field(default_factory=list)
    arrived_ambassador_ids: list[str] = Field(default_factory=list)


class StrategicMovementService:
    """
    Выполняет третий этап глобального такта: пошаговое перемещение
    армий по путям, поиск засад, движение послов и гонцов.
    """

    def __init__(self, event_bus: Optional[EventBusProtocol] = None) -> None:
        self._event_bus = event_bus

    async def process_movements_and_encounters(
        self, world_state: WorldState
    ) -> MovementStepReport:
        """
        Рассчитывает перемещения всех армий и дипломатических посланников.
        """
        moved_army_ids = []

        # =============================================================
        # Пошаговое продвижение армий
        # =============================================================

        for army in world_state.armies.values():
            if army.planned_path:
                steps_to_make = min(army.max_movement_range, len(army.planned_path))
                for _ in range(steps_to_make):
                    army.current_hex = army.planned_path.pop(0)

                moved_army_ids.append(army.id)
                if not army.planned_path:
                    army.target_hex = None

        # =============================================================
        # Проверка столкновений и засад на гексах
        # =============================================================

        encounters = await self._detect_encounters(world_state)

        # =============================================================
        # Дипломатическая логистика (депеши)
        # =============================================================

        delivered_dispatches, intercepted_dispatches = await self._process_dispatches(
            world_state
        )

        # =============================================================
        # Дипломатическая логистика (послы)
        # =============================================================

        arrived_ambassadors = await self._process_ambassadors(world_state)

        return MovementStepReport(
            moved_army_ids=moved_army_ids,
            encounters=encounters,
            delivered_dispatch_ids=delivered_dispatches,
            intercepted_dispatch_ids=intercepted_dispatches,
            arrived_ambassador_ids=arrived_ambassadors,
        )

    async def _detect_encounters(self, world_state: WorldState) -> list[EncounterEvent]:
        encounters: list[EncounterEvent] = []
        hex_armies: dict[HexCoordinates, list] = {}

        for army in world_state.armies.values():
            hex_armies.setdefault(army.current_hex, []).append(army)

        processed_pairs: set[tuple[str, str]] = set()

        for hex_coord, armies in hex_armies.items():
            if len(armies) < 2:
                continue

            for i in range(len(armies)):
                for j in range(i + 1, len(armies)):
                    army_a = armies[i]
                    army_b = armies[j]

                    if army_a.faction_id == army_b.faction_id:
                        continue

                    pair_key = (min(army_a.id, army_b.id), max(army_a.id, army_b.id))
                    if pair_key in processed_pairs:
                        continue
                    processed_pairs.add(pair_key)

                    # Проверяем дипломатические отношения
                    rel = world_state.get_relation(army_a.faction_id, army_b.faction_id)
                    is_at_war = rel is not None and rel.stance == DiplomaticStance.WAR
                    is_neutral_zone = hex_coord in world_state.neutral_hexes

                    # В Ничьей земле или при состоянии войны столкновение неизбежно
                    if is_at_war or is_neutral_zone:
                        # Расчет засады
                        is_ambush = False
                        ambusher_id = None

                        # Форсированный марш увеличивает риск попасть в засаду
                        if army_a.pace == StrategicMovementPace.FORCED:
                            is_ambush = True
                            ambusher_id = army_b.id
                        elif army_b.pace == StrategicMovementPace.FORCED:
                            is_ambush = True
                            ambusher_id = army_a.id

                        encounter = EncounterEvent(
                            hex_coordinates=hex_coord,
                            faction_a_id=army_a.faction_id,
                            faction_b_id=army_b.faction_id,
                            army_a_id=army_a.id,
                            army_b_id=army_b.id,
                            is_ambush=is_ambush,
                            ambusher_army_id=ambusher_id,
                        )
                        encounters.append(encounter)

                        if self._event_bus is not None:
                            await self._event_bus.publish(
                                "strategic.encounter_detected",
                                hex_coords=hex_coord,
                                army_a_id=army_a.id,
                                army_b_id=army_b.id,
                                is_ambush=is_ambush,
                            )

        return encounters

    async def _process_dispatches(
        self, world_state: WorldState
    ) -> tuple[list[str], list[str]]:
        delivered = []
        intercepted = []
        active_dispatches = []

        for dispatch in world_state.dispatches:
            if dispatch.travel_ticks_remaining > 0:
                dispatch.travel_ticks_remaining -= 1

            # Проверка перехвата враждебными армиями
            if not dispatch.is_intercepted and dispatch.travel_ticks_remaining > 0:
                for army in world_state.armies.values():
                    if army.faction_id not in (
                        dispatch.sender_faction_id,
                        dispatch.recipient_faction_id,
                    ):
                        # 20% шанс перехвата при нахождении в Ничьей земле
                        if army.current_hex in world_state.neutral_hexes:
                            dispatch.is_intercepted = True
                            dispatch.intercepted_by_faction_id = army.faction_id
                            intercepted.append(dispatch.id)
                            if self._event_bus is not None:
                                await self._event_bus.publish(
                                    "strategic.dispatch_intercepted",
                                    dispatch_id=dispatch.id,
                                    intercepted_by_faction_id=army.faction_id,
                                )
                            break

            if dispatch.travel_ticks_remaining == 0:
                if not dispatch.is_intercepted:
                    delivered.append(dispatch.id)
                    if self._event_bus is not None:
                        await self._event_bus.publish(
                            "strategic.dispatch_delivered",
                            dispatch_id=dispatch.id,
                            sender_faction_id=dispatch.sender_faction_id,
                            recipient_faction_id=dispatch.recipient_faction_id,
                        )
            else:
                active_dispatches.append(dispatch)

        world_state.dispatches = active_dispatches
        return delivered, intercepted

    async def _process_ambassadors(self, world_state: WorldState) -> list[str]:
        arrived = []
        for ambassador in world_state.ambassadors:
            if ambassador.status == AmbassadorStatus.TRAVELING:
                target_faction = world_state.get_faction(ambassador.target_faction_id or "")
                if target_faction is not None:
                    # Посол дошел до цитадели
                    ambassador.status = AmbassadorStatus.IN_AUDIENCE
                    arrived.append(ambassador.id)
                    if self._event_bus is not None:
                        await self._event_bus.publish(
                            "strategic.ambassador_arrived",
                            ambassador_id=ambassador.id,
                            faction_id=ambassador.faction_id,
                            target_faction_id=target_faction.id,
                        )
        return arrived
