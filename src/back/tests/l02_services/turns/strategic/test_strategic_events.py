"""
Тесты сервиса обновления событий, времени и полей брани.
"""

import pytest

from src.back.l01_domain.army.models.characters.heroes import (
    Hero,
    Scar,
)
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.combat.constants import TimeOfDay
from src.back.l01_domain.common import MechanicalModifier, StatName
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.constants import GlobalEventCategory
from src.back.l01_domain.world.models.battleground import BattlefieldLootSite
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.events import StrategicEventsService
from src.back.utils.event.registry import GameEvents


class TestStrategicEventsService:
    @pytest.mark.asyncio
    async def test_time_advancement_and_phase_shift(self, fake_bus):
        world_state = WorldState()
        world_state.time.current_hour = 12
        service = StrategicEventsService(event_bus=fake_bus)

        report = await service.process_world_events(world_state)

        assert report.ticks_elapsed == 1
        assert world_state.time.current_hour == 16
        assert report.time_of_day == TimeOfDay.NEON_HOURS
        assert report.phase_changed is True

        event_names = [name for name, _ in fake_bus.events]
        assert GameEvents.Strategic.NEON_HOURS_STARTED in event_names

    @pytest.mark.asyncio
    async def test_active_events_expiration(self, fake_bus):
        world_state = WorldState()
        event = GlobalEvent(
            id="ev_storm",
            name="Пепельная буря",
            description="...",
            category=GlobalEventCategory.WEATHER,
            duration_ticks_remaining=1,
        )
        world_state.add_event(event)
        service = StrategicEventsService(event_bus=fake_bus)

        report = await service.process_world_events(world_state)

        assert "ev_storm" in report.expired_event_ids
        assert len(world_state.active_events) == 0

    @pytest.mark.asyncio
    async def test_battlefield_decay_and_cleanup(self, fake_bus):
        world_state = WorldState()
        site = BattlefieldLootSite(
            id="site_01",
            hex_coordinates=HexCoordinates.from_axial(1, 0),
            origin_battle_id="b_1",
            salvageable_equipment={"sword": 5},
            ticks_remaining=1,
        )
        world_state.add_battlefield_site(site)
        service = StrategicEventsService(event_bus=fake_bus)

        report = await service.process_world_events(world_state)

        assert "site_01" in report.decayed_battlefield_ids
        assert len(world_state.battlefield_sites) == 0

    @pytest.mark.asyncio
    async def test_hero_recovery_after_wound(self, fake_bus):
        world_state = WorldState()
        hero = Hero.create_new(
            name="Конрад",
            faction_id="humans",
            max_hp=100.0,
            special_rule="Неукротимый",
        )
        scar = Scar(
            name="Шрам",
            description="...",
            modifier=MechanicalModifier(stat_name=StatName.ARMOR, value=1.0),
        )
        hero.apply_scar(scar, recovery_ticks=1)

        army = StrategicArmy(
            faction_id="humans",
            current_hex=HexCoordinates.from_axial(0, 0),
        )
        army.add_hero(hero)
        world_state.add_army(army)

        service = StrategicEventsService(event_bus=fake_bus)
        report = await service.process_world_events(world_state)

        assert hero.id in report.recovered_hero_ids
        assert hero.state.is_heavily_wounded is False
        assert hero.state.current_hp == 100.0
