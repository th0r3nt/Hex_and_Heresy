"""
Интеграционные тесты главного фасада мастера игры (GameMasterFacade).
"""

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.constants import GlobalEventCategory
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.game_master.custom.commanders import (
    CustomCommanderDraftResponse,
)
from src.back.l02_services.mechanics.game_master.custom.heroes import (
    CustomHeroDraftResponse,
)
from src.back.l02_services.mechanics.game_master.custom.lords import (
    CustomLordDraftResponse,
)
from src.back.l02_services.mechanics.game_master.events import (
    DynamicGlobalEventResponse,
)
from src.back.l02_services.mechanics.game_master.facade import GameMasterFacade
from src.back.tests.l02_services.mechanics.game_master.test_custom_commanders import (
    FakeLLMClient,
    FakePromptBuilder,
)
from src.back.utils.event.bus import EventBus
from src.back.utils.event.registry import GameEvents


def _setup_world() -> WorldState:
    world = WorldState()
    lord = Lord(
        faction_id="humans",
        name="Старый лорд",
        title="Барон",
    )
    faction = Faction(
        id="humans",
        race=FactionRace.HUMANS,
        name="Священная Империя",
        lord=lord,
        headquarters=Headquarters(faction_id="humans", name="Цитадель"),
        capital_hex=HexCoordinates.from_axial(0, 0),
    )
    world.add_faction(faction)
    return world


class TestGameMasterFacade:
    @pytest.mark.asyncio
    async def test_commander_creation_and_registration_in_pool(self):
        draft = CustomCommanderDraftResponse(
            is_lore_friendly=True,
            name="Капитан Маркус",
            selected_trait_ids=["pragmatist"],
        )
        llm = FakeLLMClient(draft_response=draft)
        bus = EventBus()
        events_fired: list[dict] = []

        bus.subscribe(
            GameEvents.GameMaster.CHARACTER_CREATED,
            lambda **kw: events_fired.append(kw),
        )

        facade = GameMasterFacade(
            llm_client=llm,
            prompt_builder=FakePromptBuilder(),
            event_bus=bus,
        )
        world = _setup_world()

        commander, message = await facade.create_custom_commander(
            world_state=world,
            faction_id="humans",
            biography_text="Офицер стражи.",
        )

        assert commander is not None
        assert commander.name == "Капитан Маркус"
        assert commander.id in world.available_commanders
        assert len(events_fired) == 1
        assert events_fired[0]["character_type"] == "commander"

    @pytest.mark.asyncio
    async def test_hero_creation_and_registration_in_pool(self):
        draft = CustomHeroDraftResponse(
            is_lore_friendly=True,
            name="Элара",
            special_rule="Залп картечью",
            max_hp=130.0,
            selected_trait_ids=["inquisitor"],
        )
        llm = FakeLLMClient(draft_response=draft)
        facade = GameMasterFacade(
            llm_client=llm,
            prompt_builder=FakePromptBuilder(),
        )
        world = _setup_world()

        hero, message = await facade.create_custom_hero(
            world_state=world,
            faction_id="humans",
            biography_text="Стрелок инквизиции.",
        )

        assert hero is not None
        assert hero.name == "Элара"
        assert hero.id in world.available_heroes

    @pytest.mark.asyncio
    async def test_lord_creation_and_ruler_assignment(self):
        draft = CustomLordDraftResponse(
            is_lore_friendly=True,
            name="Бенедикт",
            title="Канцлер",
            selected_trait_ids=["bureaucrat"],
        )
        llm = FakeLLMClient(draft_response=draft)
        facade = GameMasterFacade(
            llm_client=llm,
            prompt_builder=FakePromptBuilder(),
        )
        world = _setup_world()

        lord, message = await facade.create_custom_lord(
            world_state=world,
            faction_id="humans",
            biography_text="Глава канцлерата.",
            assign_as_ruler=True,
        )

        assert lord is not None
        assert lord.name == "Бенедикт"
        faction = world.get_faction("humans")
        assert faction.lord == lord
        assert faction.lord.display_name == "Канцлер Бенедикт"

    @pytest.mark.asyncio
    async def test_evaluate_world_events_facade_call(self):
        draft = DynamicGlobalEventResponse(
            should_trigger=True,
            name="Пепельный выброс",
            category=GlobalEventCategory.LORE_CRISIS,
        )
        llm = FakeLLMClient(draft_response=draft)
        facade = GameMasterFacade(
            llm_client=llm,
            prompt_builder=FakePromptBuilder(),
        )
        world = _setup_world()

        event = await facade.evaluate_world_events(world, force=True)

        assert event is not None
        assert event.name == "Пепельный выброс"
        assert len(world.active_events) == 1
