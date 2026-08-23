"""
Сервис перемещения армий по глобальной карте, проверки засад
и боевых столкновений.

Логистика депеш и послов живет в l02_services/mechanics/diplomacy и
вызывается оркестратором такта отдельным шагом.
"""

from typing import Optional

from src.back.l01_domain.army.constants import StrategicMovementPace
from src.back.l01_domain.combat.models.reports import (
    EncounterEvent,
    MovementStepReport,
)
from src.back.l01_domain.factions.constants import DiplomaticStance
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.event.registry import GameEvents


class StrategicMovementService:
    """
    Выполняет этап глобального такта: пошаговое перемещение армий
    по путям и поиск засад.
    """

    def __init__(self, event_bus: Optional[EventBusProtocol] = None) -> None:
        self._event_bus = event_bus

    async def process_movements_and_encounters(
        self, world_state: WorldState
    ) -> MovementStepReport:
        """
        Рассчитывает перемещения всех армий и столкновения между ними.
        """
        moved_army_ids = []

        # 1. Пошаговое продвижение армий
        for army in world_state.armies.values():
            if army.planned_path:
                steps_to_make = min(army.max_movement_range, len(army.planned_path))
                for _ in range(steps_to_make):
                    army.current_hex = army.planned_path.pop(0)

                moved_army_ids.append(army.id)
                if not army.planned_path:
                    army.target_hex = None

        # 2. Проверка столкновений и засад на гексах
        encounters = await self._detect_encounters(world_state)

        return MovementStepReport(
            moved_army_ids=moved_army_ids,
            encounters=encounters,
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
                        is_ambush = False
                        ambusher_id = None

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
                                GameEvents.Strategic.ENCOUNTER_DETECTED,
                                hex_coords=hex_coord,
                                army_a_id=army_a.id,
                                army_b_id=army_b.id,
                                is_ambush=is_ambush,
                            )

        return encounters
