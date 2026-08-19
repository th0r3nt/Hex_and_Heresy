"""
Тесты для src/back/l01_domain/world/models/events.py
"""

from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.constants import GlobalEventCategory, GlobalEventScope
from src.back.l01_domain.world.models.events import GlobalEvent


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
