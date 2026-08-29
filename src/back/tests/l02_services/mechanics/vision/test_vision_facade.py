"""
Пересчет тумана войны на такте.

Фасад отвечает за две вещи, которых нет ни у калькулятора, ни у фильтра:
маска обновляется на месте (прямой обзор гаснет, история растет) и о вскрытом
враге объявляется ровно один раз, а не каждый такт подряд.
"""

import pytest

from src.back.l01_domain.maps.constants import HexVisibilityState
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.vision.facade import VisionFacade
from src.back.tests.l02_services.mechanics.vision.conftest import (
    PLAYER_CAPITAL,
    FakeEventBus,
    add_army,
    hex_at,
)
from src.back.utils.event.registry import GameEvents

VISION_UPDATED = GameEvents.Strategic.VISION_UPDATED.value
ARMY_SPOTTED = GameEvents.Strategic.ARMY_SPOTTED.value


@pytest.fixture
def facade(fake_bus: FakeEventBus) -> VisionFacade:
    return VisionFacade(event_bus=fake_bus)


# ==================================================================
# ОБНОВЛЕНИЕ МАСОК
# ==================================================================


class TestWorldVisionRefresh:
    async def test_every_faction_gets_its_own_mask(
        self, facade: VisionFacade, world: WorldState
    ):
        await facade.refresh_world_vision(world)

        assert set(world.vision_maps) == {"humans", "greenskins"}

    async def test_report_counts_what_each_side_sees(
        self, facade: VisionFacade, world: WorldState
    ):
        report = await facade.refresh_world_vision(world)

        # Цитадель радиусом 2 - это 19 гексов, и все они открыты впервые
        assert report.visible_hexes_by_faction["humans"] == 19
        assert report.newly_explored_by_faction["humans"] == 19

    async def test_second_tick_opens_nothing_new(
        self, facade: VisionFacade, world: WorldState
    ):
        """Стоящая на месте держава новых земель не открывает."""
        await facade.refresh_world_vision(world)
        report = await facade.refresh_world_vision(world)

        assert report.newly_explored_by_faction["humans"] == 0
        assert report.visible_hexes_by_faction["humans"] == 19

    async def test_marching_army_grows_the_explored_history(
        self, facade: VisionFacade, world: WorldState
    ):
        """Разъезд ушел вперед - карта пополнилась его находками."""
        await facade.refresh_world_vision(world)
        scouts = add_army(world, "humans", hex_at(6))

        report = await facade.refresh_world_vision(world)

        assert report.newly_explored_by_faction["humans"] == 7
        assert scouts.current_hex in world.get_or_create_vision_map("humans").explored_hexes

    async def test_leaving_hex_turns_it_into_fog(
        self, facade: VisionFacade, world: WorldState
    ):
        """
        Ушедшая армия оставляет за собой туман войны, а не черноту: местность
        уже известна, но что по ней ходит - больше не видно.
        """
        scouts = add_army(world, "humans", hex_at(6))
        await facade.refresh_world_vision(world)

        world.remove_army(scouts.id)
        await facade.refresh_world_vision(world)

        assert (
            facade.get_hex_status(world, "humans", hex_at(6))
            == HexVisibilityState.FOG_OF_WAR
        )

    async def test_home_stays_visible_through_the_ticks(
        self, facade: VisionFacade, world: WorldState
    ):
        await facade.refresh_world_vision(world)
        await facade.refresh_world_vision(world)

        assert (
            facade.get_hex_status(world, "humans", PLAYER_CAPITAL)
            == HexVisibilityState.VISIBLE
        )
        assert facade.is_hex_visible(world, "humans", PLAYER_CAPITAL)


# ==================================================================
# ВСКРЫТИЕ ЧУЖИХ АРМИЙ
# ==================================================================


class TestSpottingEnemies:
    async def test_enemy_walking_into_the_watch_ring_is_reported(
        self, facade: VisionFacade, world: WorldState, fake_bus: FakeEventBus
    ):
        await facade.refresh_world_vision(world)

        raiders = add_army(world, "greenskins", hex_at(2))
        report = await facade.refresh_world_vision(world)

        assert report.spotted_army_ids_by_faction["humans"] == [raiders.id]
        assert ARMY_SPOTTED in fake_bus.names()

    async def test_enemy_beyond_the_ring_is_not_reported(
        self, facade: VisionFacade, world: WorldState, fake_bus: FakeEventBus
    ):
        await facade.refresh_world_vision(world)

        add_army(world, "greenskins", hex_at(5))
        report = await facade.refresh_world_vision(world)

        assert "humans" not in report.spotted_army_ids_by_faction
        assert ARMY_SPOTTED not in fake_bus.names()

    async def test_standing_enemy_is_announced_only_once(
        self, facade: VisionFacade, world: WorldState, fake_bus: FakeEventBus
    ):
        """
        Враг, который так и стоит под стенами, тревогу второй раз не поднимает:
        иначе лента событий гудела бы каждый такт.
        """
        await facade.refresh_world_vision(world)
        add_army(world, "greenskins", hex_at(2))

        await facade.refresh_world_vision(world)
        await facade.refresh_world_vision(world)

        assert len(fake_bus.payloads(ARMY_SPOTTED)) == 1

    async def test_returning_enemy_raises_the_alarm_again(
        self, facade: VisionFacade, world: WorldState, fake_bus: FakeEventBus
    ):
        """
        Ушедший из обзора и вернувшийся враг - снова новость: разведка не
        обязана помнить, что он тут уже был.
        """
        await facade.refresh_world_vision(world)
        raiders = add_army(world, "greenskins", hex_at(2))
        await facade.refresh_world_vision(world)

        raiders.current_hex = hex_at(6)
        await facade.refresh_world_vision(world)
        raiders.current_hex = hex_at(2)
        report = await facade.refresh_world_vision(world)

        assert report.spotted_army_ids_by_faction["humans"] == [raiders.id]
        assert len(fake_bus.payloads(ARMY_SPOTTED)) == 2

    async def test_spotting_event_names_its_observer(
        self, facade: VisionFacade, world: WorldState, fake_bus: FakeEventBus
    ):
        """
        В событии указано, чьи глаза увидели врага: по этому полю лента
        и отсеивает чужие находки.
        """
        await facade.refresh_world_vision(world)
        raiders = add_army(world, "greenskins", hex_at(2), name="Орда Клыка")

        await facade.refresh_world_vision(world)
        payload = fake_bus.payloads(ARMY_SPOTTED)[0]

        assert payload["observer_faction_id"] == "humans"
        assert payload["owner_faction_id"] == "greenskins"
        assert payload["army_id"] == raiders.id
        assert payload["hex_coords"] == hex_at(2)

    async def test_own_army_is_never_spotted(
        self, facade: VisionFacade, world: WorldState, fake_bus: FakeEventBus
    ):
        await facade.refresh_world_vision(world)
        add_army(world, "humans", hex_at(2))

        report = await facade.refresh_world_vision(world)

        assert "humans" not in report.spotted_army_ids_by_faction


# ==================================================================
# ОБЪЯВЛЕНИЯ ОБ ОБНОВЛЕНИИ ТУМАНА
# ==================================================================


class TestVisionEvents:
    async def test_first_tick_announces_the_opened_map(
        self, facade: VisionFacade, world: WorldState, fake_bus: FakeEventBus
    ):
        await facade.refresh_world_vision(world)

        payloads = fake_bus.payloads(VISION_UPDATED)

        assert len(payloads) == 2  # обе стороны открыли свои окрестности
        assert payloads[0]["visible_hexes_count"] == 19

    async def test_unchanged_fog_stays_silent(
        self, facade: VisionFacade, world: WorldState, fake_bus: FakeEventBus
    ):
        """Перерисовывать неизменившийся туман интерфейсу незачем."""
        await facade.refresh_world_vision(world)
        fake_bus.events.clear()

        await facade.refresh_world_vision(world)

        assert fake_bus.payloads(VISION_UPDATED) == []

    async def test_facade_works_without_a_bus(self, world: WorldState):
        """Без шины фасад просто молчит, но обзор считает как обычно."""
        silent = VisionFacade()

        report = await silent.refresh_world_vision(world)

        assert report.visible_hexes_by_faction["humans"] == 19


# ==================================================================
# ЧТЕНИЕ ОБЗОРА
# ==================================================================


class TestVisionReading:
    def test_unknown_faction_sees_black_fog(
        self, facade: VisionFacade, world: WorldState
    ):
        assert (
            facade.get_hex_status(world, "humans", hex_at(9))
            == HexVisibilityState.UNEXPLORED
        )

    def test_mask_is_created_on_first_request(
        self, facade: VisionFacade, world: WorldState
    ):
        """
        Фракция, которая еще не считала обзор, получает пустую маску, а не
        отказ: смотреть ей просто нечем.
        """
        vision_map = facade.get_vision_map(world, "greenskins")

        assert vision_map.faction_id == "greenskins"
        assert vision_map.visible_hexes == set()
