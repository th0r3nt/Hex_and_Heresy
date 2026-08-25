"""
Тесты для src/back/l01_domain/world/models/events.py
"""

from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.constants import GlobalEventCategory, GlobalEventScope
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.models.reports import EventsStepReport


class TestGlobalEvent:
    def test_global_scope_affects_all(self):
        event = GlobalEvent(
            name="Магнитная буря",
            description="Северное сияние ослепляет магов.",
            category=GlobalEventCategory.WEATHER,
            scope=GlobalEventScope.GLOBAL,
        )

        assert event.affects_faction("faction_humans")
        assert event.affects_faction("faction_elfs")
        assert event.affects_hex(HexCoordinates.from_axial(0, 0))

    def test_faction_scope_filtering(self):
        event = GlobalEvent(
            name="Бунт в шахтах",
            description="Рабочие требуют хлеба.",
            category=GlobalEventCategory.ECONOMIC,
            scope=GlobalEventScope.FACTION,
            target_faction_ids=["faction_humans"],
        )

        assert event.affects_faction("faction_humans")
        assert not event.affects_faction("faction_orcs")

    def test_zone_scope_filtering(self):
        target_hex = HexCoordinates.from_axial(2, -1)
        event = GlobalEvent(
            name="Выброс пепла",
            description="Токсичное облако над долиной.",
            category=GlobalEventCategory.LORE_CRISIS,
            scope=GlobalEventScope.ZONE,
            target_hex_coords=[target_hex],
        )

        assert event.affects_hex(target_hex)
        assert not event.affects_hex(HexCoordinates.from_axial(0, 0))

    def test_duration_ticking_and_expiration(self):
        event = GlobalEvent(
            name="Кратковременный туман",
            description="Видимость снижена.",
            category=GlobalEventCategory.WEATHER,
            duration_ticks_remaining=2,
        )

        assert event.is_active
        event.tick()
        assert event.duration_ticks_remaining == 1
        assert event.is_active

        event.tick()
        assert event.duration_ticks_remaining == 0
        assert not event.is_active

    def test_event_with_spawned_army_and_hex(self):
        spawn_point = HexCoordinates.from_axial(4, 2)
        event = GlobalEvent(
            name="Орочий набег",
            description="Орда движется к границам.",
            category=GlobalEventCategory.MILITARY,
            scope=GlobalEventScope.ZONE,
            target_hex_coords=[spawn_point],
            spawned_army_id="army_orcs_raiders_01",
            spawn_hex=spawn_point,
        )

        assert event.spawned_army_id == "army_orcs_raiders_01"
        assert event.spawn_hex == spawn_point
        assert event.affects_hex(spawn_point) is True


class TestEventsStepReport:
    def test_events_step_report_carries_new_events_and_spawned_armies(self):
        event = GlobalEvent(
            name="Восстание рабов",
            description="...",
            category=GlobalEventCategory.ECONOMIC,
            spawned_army_id="army_rebels_99",
        )

        report = EventsStepReport(
            current_timestamp="День 1, 00:00",
            time_of_day="grey_hours",
            new_events=[event],
            spawned_army_ids=["army_rebels_99"],
        )

        assert len(report.new_events) == 1
        assert report.new_events[0].name == "Восстание рабов"
        assert report.spawned_army_ids == ["army_rebels_99"]
