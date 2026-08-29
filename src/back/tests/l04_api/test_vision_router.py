"""
Эндпоинты тумана войны.

Здесь работает настоящий TurnsFacade: проверяется, что слой карты и срез
мира доезжают до клиента уже отфильтрованными, а не сырым WorldState.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.constants import HexVisibilityState
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.vision.facade import VisionFacade
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.tests.l04_api.conftest import FakeContainer


def hex_at(q: int) -> HexCoordinates:
    return HexCoordinates.from_axial(q, 0)


def _faction(world_state: WorldState, faction_id: str, is_player: bool, q: int) -> Faction:
    faction = Faction(
        id=faction_id,
        race=FactionRace.HUMANS,
        name=f"Держава {faction_id}",
        is_player_controlled=is_player,
        lord=Lord(faction_id=faction_id, name="Лорд", title="Правитель"),
        headquarters=Headquarters(faction_id=faction_id, name="Цитадель"),
        capital_hex=hex_at(q),
    )
    world_state.add_faction(faction)
    return faction


@pytest.fixture
async def party(container: FakeContainer, active_party: WorldState) -> WorldState:
    """
    Идущая партия с уже посчитанным туманом: игрок на западе, соперник
    на востоке, между ними двенадцать гексов Ничьей земли.
    """
    container.turns_facade = TurnsFacade()
    _faction(active_party, "humans", is_player=True, q=0)
    _faction(active_party, "greenskins", is_player=False, q=12)

    await VisionFacade().refresh_world_vision(active_party)
    return active_party


# ==================================================================
# СЛОЙ ТУМАНА
# ==================================================================


class TestVisionEndpoint:
    async def test_vision_returns_the_players_mask(
        self, client: TestClient, party: WorldState
    ):
        response = client.get("/api/strategic/vision")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["faction_id"] == "humans"
        assert body["visible_count"] == 19
        assert len(body["visible_hexes"]) == 19

    async def test_fogged_hexes_do_not_duplicate_the_visible_ones(
        self, client: TestClient, party: WorldState
    ):
        """
        Клиент рисует прямой обзор поверх разведанного, поэтому один и тот
        же гекс не должен приезжать в обоих списках.
        """
        scouts = StrategicArmy(
            faction_id="humans", name="Разъезд", current_hex=hex_at(6)
        )
        party.add_army(scouts)
        await VisionFacade().refresh_world_vision(party)

        party.remove_army(scouts.id)
        await VisionFacade().refresh_world_vision(party)

        body = client.get("/api/strategic/vision").json()
        visible = {tuple(h.values()) for h in body["visible_hexes"]}
        fogged = {tuple(h.values()) for h in body["explored_hexes"]}

        assert visible & fogged == set()
        assert body["explored_count"] == 26  # 19 у цитадели + 7 у ушедшего разъезда

    def test_party_without_a_player_is_an_error(
        self, client: TestClient, container: FakeContainer, active_party: WorldState
    ):
        """Смотреть на карту глазами некому - это честная ошибка, а не пустой слой."""
        container.turns_facade = TurnsFacade()
        _faction(active_party, "greenskins", is_player=False, q=12)

        response = client.get("/api/strategic/vision")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================================================================
# СОСТОЯНИЕ ОДНОГО ГЕКСА
# ==================================================================


class TestHexVisibilityEndpoint:
    async def test_watched_hex_is_visible(self, client: TestClient, party: WorldState):
        response = client.get("/api/strategic/vision/hex", params={"q": 2, "r": 0})

        assert response.json()["state"] == HexVisibilityState.VISIBLE.value

    async def test_untouched_hex_is_black(self, client: TestClient, party: WorldState):
        response = client.get("/api/strategic/vision/hex", params={"q": 9, "r": 0})

        assert response.json()["state"] == HexVisibilityState.UNEXPLORED.value


# ==================================================================
# СРЕЗ МИРА
# ==================================================================


class TestWorldViewEndpoint:
    async def test_view_hides_the_enemy_beyond_the_horizon(
        self, client: TestClient, party: WorldState
    ):
        raiders = StrategicArmy(
            faction_id="greenskins", name="Орда", current_hex=hex_at(9)
        )
        party.add_army(raiders)
        await VisionFacade().refresh_world_vision(party)

        body = client.get("/api/strategic/world-view").json()

        assert raiders.id not in body["armies"]

    async def test_view_shows_the_enemy_under_the_walls(
        self, client: TestClient, party: WorldState
    ):
        raiders = StrategicArmy(
            faction_id="greenskins", name="Орда", current_hex=hex_at(2)
        )
        party.add_army(raiders)
        await VisionFacade().refresh_world_vision(party)

        body = client.get("/api/strategic/world-view").json()

        assert raiders.id in body["armies"]

    async def test_view_masks_the_enemy_capital(
        self, client: TestClient, party: WorldState
    ):
        body = client.get("/api/strategic/world-view").json()

        assert body["factions"]["greenskins"]["capital_hex"] is None
        assert body["factions"]["humans"]["capital_hex"] is not None

    async def test_view_carries_only_the_players_mask(
        self, client: TestClient, party: WorldState
    ):
        body = client.get("/api/strategic/world-view").json()

        assert list(body["vision_maps"]) == ["humans"]

    async def test_view_does_not_touch_the_real_world(
        self, client: TestClient, party: WorldState
    ):
        """Срез - копия: после запроса сам мир соперника не теряет."""
        client.get("/api/strategic/world-view")

        assert party.factions["greenskins"].capital_hex == hex_at(12)
