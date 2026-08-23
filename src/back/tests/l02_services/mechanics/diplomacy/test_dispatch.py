"""
Тесты депеш: расчет маршрута и цены, доставка по тактам и перехват гонца
чужой армией на пути.
"""

from random import Random

import pytest

from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.exceptions import (
    FactionCapitalUnknownError,
    InsufficientResourcesError,
    SelfDiplomacyForbiddenError,
)
from src.back.l01_domain.factions.constants import (
    DISPATCH_BASE_COST_GOLD,
    DISPATCH_COST_GOLD_PER_HEX,
    ResourceType,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l02_services.mechanics.diplomacy.messenger import DispatchService
from src.back.utils.event.registry import GameEvents


class AlwaysIntercepts(Random):
    """Бросок кубика, который всегда проваливает проверку скрытности гонца."""

    def random(self) -> float:
        return 0.0


class NeverIntercepts(Random):
    """Гонец всегда проходит незамеченным."""

    def random(self) -> float:
        return 1.0


class TestDispatchSending:
    @pytest.mark.asyncio
    async def test_route_cost_and_eta_are_calculated_on_send(self, world, humans, fake_bus):
        service = DispatchService(event_bus=fake_bus, rng=NeverIntercepts())
        gold_before = humans.resources[ResourceType.GOLD]

        dispatch = await service.send(world, "humans", "elfs", "Предлагаю мир.")

        # Восемь гексов пути при скорости гонца 4 гекса за такт
        assert len(dispatch.route) == 8
        assert dispatch.route[-1] == HexCoordinates.from_axial(8, 0)
        assert dispatch.total_travel_ticks == 2
        assert dispatch.travel_ticks_remaining == 2

        expected_cost = DISPATCH_BASE_COST_GOLD + DISPATCH_COST_GOLD_PER_HEX * 8
        assert dispatch.cost_gold == expected_cost
        assert humans.resources[ResourceType.GOLD] == gold_before - expected_cost
        assert world.dispatches == [dispatch]
        assert GameEvents.Diplomacy.DISPATCH_SENT in fake_bus.names()

    @pytest.mark.asyncio
    async def test_dispatch_to_self_is_forbidden(self, world):
        service = DispatchService()

        with pytest.raises(SelfDiplomacyForbiddenError):
            await service.send(world, "humans", "humans", "Сам себе пишу.")

    @pytest.mark.asyncio
    async def test_faction_without_capital_cannot_be_reached(self, world):
        service = DispatchService()

        with pytest.raises(FactionCapitalUnknownError):
            await service.send(world, "humans", "greenskins", "Где вы вообще?")

    @pytest.mark.asyncio
    async def test_empty_treasury_blocks_courier(self, world, humans):
        humans.resources[ResourceType.GOLD] = 5.0
        service = DispatchService()

        with pytest.raises(InsufficientResourcesError):
            await service.send(world, "humans", "elfs", "Гонцу платить нечем.")

        assert world.dispatches == []


class TestDispatchDelivery:
    @pytest.mark.asyncio
    async def test_dispatch_arrives_after_two_ticks(self, world, fake_bus):
        service = DispatchService(event_bus=fake_bus, rng=NeverIntercepts())
        dispatch = await service.send(world, "humans", "elfs", "Предлагаю мир.")

        delivered, intercepted = await service.process_tick(world)
        assert delivered == [] and intercepted == []
        assert dispatch.travel_ticks_remaining == 1
        assert len(dispatch.route) == 4

        delivered, intercepted = await service.process_tick(world)
        assert [d.id for d in delivered] == [dispatch.id]
        assert world.dispatches == []
        assert GameEvents.Strategic.DISPATCH_DELIVERED in fake_bus.names()

    @pytest.mark.asyncio
    async def test_hostile_army_on_route_intercepts_letter(self, world, elfs, fake_bus):
        # Орочий патруль стоит на втором гексе маршрута
        world.add_army(
            StrategicArmy(
                faction_id="greenskins", current_hex=HexCoordinates.from_axial(2, 0)
            )
        )
        service = DispatchService(event_bus=fake_bus, rng=AlwaysIntercepts())
        dispatch = await service.send(world, "humans", "elfs", "Тайный план.")

        delivered, intercepted = await service.process_tick(world)

        assert delivered == []
        assert [d.id for d in intercepted] == [dispatch.id]
        assert dispatch.is_intercepted is True
        assert dispatch.intercepted_by_faction_id == "greenskins"
        # Письмо ушло в разведтрофеи орков и не дошло до адресата
        assert world.intercepted_dispatches["greenskins"] == [dispatch]
        assert world.dispatches == []
        assert GameEvents.Strategic.DISPATCH_INTERCEPTED in fake_bus.names()
        assert GameEvents.Strategic.DISPATCH_DELIVERED not in fake_bus.names()

    @pytest.mark.asyncio
    async def test_sender_and_recipient_armies_never_intercept(self, world, fake_bus):
        # На маршруте стоят армии обеих сторон переписки
        world.add_army(
            StrategicArmy(faction_id="humans", current_hex=HexCoordinates.from_axial(1, 0))
        )
        world.add_army(
            StrategicArmy(faction_id="elfs", current_hex=HexCoordinates.from_axial(5, 0))
        )
        service = DispatchService(event_bus=fake_bus, rng=AlwaysIntercepts())
        dispatch = await service.send(world, "humans", "elfs", "Свои не перехватывают.")

        await service.process_tick(world)
        delivered, intercepted = await service.process_tick(world)

        assert intercepted == []
        assert [d.id for d in delivered] == [dispatch.id]

    @pytest.mark.asyncio
    async def test_courier_is_not_checked_on_home_hex(self, world, fake_bus):
        # Чужая армия стоит прямо в цитадели отправителя - гекс отправления
        # в маршрут не входит, так что перехвата тут быть не может
        world.add_army(
            StrategicArmy(
                faction_id="greenskins", current_hex=HexCoordinates.from_axial(0, 0)
            )
        )
        service = DispatchService(event_bus=fake_bus, rng=AlwaysIntercepts())
        dispatch = await service.send(world, "humans", "elfs", "Выезжаю из дома.")

        _, intercepted = await service.process_tick(world)

        assert intercepted == []
        assert dispatch.is_intercepted is False
