"""
Тесты генератора динамических событий мира и кризисов.
"""

import pytest

from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.world.constants import GlobalEventCategory, GlobalEventScope
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.game_master.events import (
    DynamicEventService,
    DynamicGlobalEventResponse,
)
from src.back.tests.l02_services.mechanics.game_master.test_custom_commanders import (
    FakeLLMClient,
    FakePromptBuilder,
)
from src.back.utils.event.bus import EventBus
from src.back.utils.event.registry import GameEvents


class DummyGameData(GameDataRepositoryProtocol):
    def get_unit_archetype(self, unit_id: str):
        return UnitArchetype(
            id=unit_id,
            race=FactionRace.NEUTRALS,
            faction_id="neutrals",
            name="Толпа бунтовщиков",
            tier=0,
            default_unit_count=100,
            base_stats=BaseUnitStats(max_hp=10.0),
        )

    def get_equipment(self, equipment_id: str):
        return None

    def get_building(self, building_id: str):
        return None

    def list_faction_units(self, faction_id: str):
        return []

    def list_faction_equipment(self, faction_id: str):
        return []

    def list_faction_buildings(self, faction_id: str):
        return []


def _make_world() -> WorldState:
    world = WorldState()
    lord = Lord(
        faction_id="humans",
        name="Лорд",
        title="Барон",
    )
    faction = Faction(
        id="humans",
        race=FactionRace.HUMANS,
        name="Империя",
        lord=lord,
        headquarters=Headquarters(faction_id="humans", name="Цитадель"),
        capital_hex=HexCoordinates.from_axial(0, 0),
    )
    world.add_faction(faction)
    world.neutral_hexes.append(HexCoordinates.from_axial(2, 0))
    return world


class TestDynamicEventsService:
    @pytest.mark.asyncio
    async def test_non_military_weather_event_spawn(self):
        draft = DynamicGlobalEventResponse(
            should_trigger=True,
            name="Магнитная буря",
            description="Небо вспыхнуло ядовитым сиянием.",
            category=GlobalEventCategory.WEATHER,
            scope=GlobalEventScope.GLOBAL,
            duration_ticks=3,
        )
        world = _make_world()
        bus = EventBus()
        events_published: list[str] = []

        bus.subscribe(
            GameEvents.GameMaster.GLOBAL_EVENT_SPAWNED,
            lambda **kw: events_published.append(kw.get("name", "")),
        )

        service = DynamicEventService(
            llm_client=FakeLLMClient(draft_response=draft),
            prompt_builder=FakePromptBuilder(),
            event_bus=bus,
        )

        event = await service.evaluate_and_spawn_event(world, force=True)

        assert event is not None
        assert event.name == "Магнитная буря"
        assert event.category == GlobalEventCategory.WEATHER
        assert len(world.active_events) == 1
        assert "Магнитная буря" in events_published

    @pytest.mark.asyncio
    async def test_military_event_spawns_hostile_army_on_map(self):
        draft = DynamicGlobalEventResponse(
            should_trigger=True,
            name="Голодный бунт",
            description="Крестьяне подняли вилы против барона.",
            category=GlobalEventCategory.ECONOMIC,
            scope=GlobalEventScope.ZONE,
            target_hex_q=2,
            target_hex_r=0,
            spawn_hostile_army=True,
            neutral_army_name="Орда бунтовщиков",
            neutral_unit_type="rebels",
        )
        world = _make_world()
        service = DynamicEventService(
            llm_client=FakeLLMClient(draft_response=draft),
            prompt_builder=FakePromptBuilder(),
            gamedata_repository=DummyGameData(),
        )

        event = await service.evaluate_and_spawn_event(world, force=True)

        assert event is not None
        assert event.spawned_army_id is not None
        assert event.spawn_hex == HexCoordinates.from_axial(2, 0)

        spawned_army = world.get_army(event.spawned_army_id)
        assert spawned_army is not None
        assert spawned_army.faction_id == "neutrals"
        assert spawned_army.current_hex == HexCoordinates.from_axial(2, 0)
        assert len(spawned_army.squads) == 1
        assert spawned_army.squads[0].display_name == "Толпа бунтовщиков"

    @pytest.mark.asyncio
    async def test_skip_when_should_trigger_is_false(self):
        draft = DynamicGlobalEventResponse(
            should_trigger=False,
            name="",
        )
        world = _make_world()
        service = DynamicEventService(
            llm_client=FakeLLMClient(draft_response=draft),
            prompt_builder=FakePromptBuilder(),
        )

        event = await service.evaluate_and_spawn_event(world, force=True)

        assert event is None
        assert len(world.active_events) == 0
