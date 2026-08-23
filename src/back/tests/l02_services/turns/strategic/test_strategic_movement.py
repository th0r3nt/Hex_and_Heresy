"""
Тесты перемещений армий и обнаружения столкновений на глобальной карте.
"""

import pytest

from src.back.l01_domain.army.constants import StrategicMovementPace
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.movement import StrategicMovementService


class TestStrategicMovementService:
    @pytest.mark.asyncio
    async def test_army_step_movement_along_path(self, human_faction, fake_bus):
        path = [
            HexCoordinates.from_axial(1, 0),
            HexCoordinates.from_axial(2, 0),
            HexCoordinates.from_axial(3, 0),
        ]
        army = StrategicArmy(
            faction_id=human_faction.id,
            current_hex=HexCoordinates.from_axial(0, 0),
            planned_path=list(path),
            pace=StrategicMovementPace.MARCH,  # дальность 2 гекса
        )
        world_state = WorldState()
        world_state.add_army(army)

        service = StrategicMovementService(event_bus=fake_bus)
        report = await service.process_movements_and_encounters(world_state)

        assert army.id in report.moved_army_ids
        assert army.current_hex == HexCoordinates.from_axial(2, 0)
        assert len(army.planned_path) == 1

    @pytest.mark.asyncio
    async def test_encounter_and_ambush_detection_in_neutral_lands(
        self, human_faction, orc_faction, fake_bus
    ):
        neutral_hex = HexCoordinates.from_axial(5, 5)
        army_human = StrategicArmy(
            faction_id=human_faction.id,
            current_hex=neutral_hex,
            pace=StrategicMovementPace.FORCED,  # уязвимость к засаде
        )
        army_orc = StrategicArmy(
            faction_id=orc_faction.id,
            current_hex=neutral_hex,
            pace=StrategicMovementPace.CAUTIOUS,
        )

        world_state = WorldState()
        world_state.neutral_hexes.append(neutral_hex)
        world_state.add_faction(human_faction)
        world_state.add_faction(orc_faction)
        world_state.add_army(army_human)
        world_state.add_army(army_orc)

        service = StrategicMovementService(event_bus=fake_bus)
        report = await service.process_movements_and_encounters(world_state)

        assert len(report.encounters) == 1
        encounter = report.encounters[0]
        assert encounter.hex_coordinates == neutral_hex
        assert encounter.is_ambush is True
        assert encounter.ambusher_army_id == army_orc.id
