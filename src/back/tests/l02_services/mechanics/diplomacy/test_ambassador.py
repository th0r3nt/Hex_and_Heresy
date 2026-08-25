"""
Тесты послов: маршрут до чужой цитадели, движение с охраной и без,
начало аудиенции и казнь послa чужим лордом.
"""

import pytest

from src.back.l01_domain.army.constants import StrategicMovementPace
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.exceptions.diplomacy import (
    AmbassadorUnavailableError,
    FactionCapitalUnknownError,
    SelfDiplomacyForbiddenError,
)
from src.back.l01_domain.factions.constants import (
    AmbassadorStatus,
    DiplomaticStance,
    NegotiationMode,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l02_services.mechanics.diplomacy.ambassador import AmbassadorService
from src.back.utils.event.registry import GameEvents


class TestAmbassadorTravel:
    @pytest.mark.asyncio
    async def test_send_builds_route_from_capital_to_capital(self, world, fake_bus):
        service = AmbassadorService(event_bus=fake_bus)

        ambassador = await service.send(
            world,
            faction_id="humans",
            name="Граф Вальтер",
            target_faction_id="elfs",
            traits=["Красноречивый"],
            negotiation_mode=NegotiationMode.AUTOMATIC,
            directive="Выторгуй право прохода за 500 золота.",
        )

        assert ambassador.current_hex == HexCoordinates.from_axial(0, 0)
        assert len(ambassador.planned_path) == 8
        assert ambassador.planned_path[-1] == HexCoordinates.from_axial(8, 0)
        assert ambassador.status == AmbassadorStatus.TRAVELING
        assert world.ambassadors == [ambassador]
        assert GameEvents.Diplomacy.AMBASSADOR_SENT in fake_bus.names()

    @pytest.mark.asyncio
    async def test_ambassador_to_self_is_forbidden(self, world):
        service = AmbassadorService()

        with pytest.raises(SelfDiplomacyForbiddenError):
            await service.send(world, "humans", "Сам себе посол", "humans")

    @pytest.mark.asyncio
    async def test_faction_without_capital_cannot_host_ambassador(self, world):
        service = AmbassadorService()

        with pytest.raises(FactionCapitalUnknownError):
            await service.send(world, "humans", "Граф Вальтер", "greenskins")

    @pytest.mark.asyncio
    async def test_foot_ambassador_walks_two_hexes_per_tick(self, world, fake_bus):
        service = AmbassadorService(event_bus=fake_bus)
        ambassador = await service.send(world, "humans", "Граф Вальтер", "elfs")

        arrived = await service.process_tick(world)

        assert arrived == []
        assert ambassador.current_hex == HexCoordinates.from_axial(2, 0)
        assert len(ambassador.planned_path) == 6

    @pytest.mark.asyncio
    async def test_escort_sets_the_pace_and_follows_ambassador(self, world, fake_bus):
        escort = StrategicArmy(
            faction_id="humans",
            current_hex=HexCoordinates.from_axial(0, 0),
            pace=StrategicMovementPace.MOUNTED,  # 4 гекса за такт
        )
        world.add_army(escort)

        service = AmbassadorService(event_bus=fake_bus)
        ambassador = await service.send(
            world, "humans", "Граф Вальтер", "elfs", escort_army_id=escort.id
        )

        await service.process_tick(world)

        assert ambassador.current_hex == HexCoordinates.from_axial(4, 0)
        assert escort.current_hex == ambassador.current_hex

    @pytest.mark.asyncio
    async def test_arrival_opens_audience(self, world, fake_bus):
        service = AmbassadorService(event_bus=fake_bus)
        ambassador = await service.send(world, "humans", "Граф Вальтер", "elfs")

        for _ in range(4):
            arrived = await service.process_tick(world)

        assert [a.id for a in arrived] == [ambassador.id]
        assert ambassador.status == AmbassadorStatus.IN_AUDIENCE
        assert ambassador.current_hex == HexCoordinates.from_axial(8, 0)
        assert GameEvents.Strategic.AMBASSADOR_ARRIVED in fake_bus.names()

        # Дошедший посол больше не двигается
        assert await service.process_tick(world) == []


class TestAmbassadorFate:
    @pytest.mark.asyncio
    async def test_execution_starts_a_war(self, world, fake_bus):
        service = AmbassadorService(event_bus=fake_bus)
        ambassador = await service.send(world, "humans", "Граф Вальтер", "elfs")
        for _ in range(4):
            await service.process_tick(world)

        executed = await service.execute_ambassador(world, ambassador.id)

        assert executed.status == AmbassadorStatus.EXECUTED
        assert world.ambassadors == []
        relation = world.get_relation("humans", "elfs")
        assert relation is not None
        assert relation.stance == DiplomaticStance.WAR
        assert GameEvents.Diplomacy.AMBASSADOR_EXECUTED in fake_bus.names()
        assert GameEvents.Diplomacy.WAR_DECLARED in fake_bus.names()

    @pytest.mark.asyncio
    async def test_ambassador_in_transit_cannot_be_executed(self, world):
        service = AmbassadorService()
        ambassador = await service.send(world, "humans", "Граф Вальтер", "elfs")

        with pytest.raises(AmbassadorUnavailableError):
            await service.execute_ambassador(world, ambassador.id)

    @pytest.mark.asyncio
    async def test_send_home_removes_ambassador_from_map(self, world):
        service = AmbassadorService()
        ambassador = await service.send(world, "humans", "Граф Вальтер", "elfs")

        returned = await service.send_home(world, ambassador.id)

        assert returned.status == AmbassadorStatus.RETURNED
        assert world.ambassadors == []
