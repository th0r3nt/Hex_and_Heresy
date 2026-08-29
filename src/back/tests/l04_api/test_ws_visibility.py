"""
Гейт тумана войны перед лентой событий.

Список BROADCAST_EVENTS решает, какие события вообще едут клиенту, а гейт -
какие из них игрок имеет право увидеть. Здесь проверяется именно второй
рубеж: чужой марш в неразведанном секторе до окна клиента не доезжает.
"""

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.gameflow.facade import GameFlowFacade
from src.back.l02_services.mechanics.vision.facade import VisionFacade
from src.back.l04_api.ws.dispatcher import EventDispatcher
from src.back.l04_api.ws.manager import ConnectionManager
from src.back.l04_api.ws.schemas import ServerMessage
from src.back.l04_api.ws.visibility import PlayerVisionGate
from src.back.utils.event.registry import GameEvents

ENCOUNTER = GameEvents.Strategic.ENCOUNTER_DETECTED.value
ARMY_SPOTTED = GameEvents.Strategic.ARMY_SPOTTED.value


def hex_at(q: int) -> HexCoordinates:
    return HexCoordinates.from_axial(q, 0)


class FakeManager(ConnectionManager):
    """Менеджер, который вместо отправки складывает сообщения в список."""

    def __init__(self) -> None:
        super().__init__()
        self.sent: list[ServerMessage] = []

    async def broadcast(self, message: ServerMessage) -> None:
        self.sent.append(message)

    def events(self) -> list[str]:
        return [message.event for message in self.sent]


def build_faction(faction_id: str, is_player: bool) -> Faction:
    return Faction(
        id=faction_id,
        race=FactionRace.HUMANS,
        name=f"Держава {faction_id}",
        is_player_controlled=is_player,
        lord=Lord(faction_id=faction_id, name="Лорд", title="Правитель"),
        headquarters=Headquarters(faction_id=faction_id, name="Цитадель"),
        capital_hex=hex_at(0 if is_player else 12),
    )


@pytest.fixture
def world() -> WorldState:
    world_state = WorldState()
    world_state.add_faction(build_faction("humans", is_player=True))
    world_state.add_faction(build_faction("greenskins", is_player=False))
    return world_state


@pytest.fixture
def gameflow(world: WorldState) -> GameFlowFacade:
    facade = GameFlowFacade()
    facade.bind_world_state(world)
    return facade


@pytest.fixture
async def lit_world(world: WorldState) -> WorldState:
    """Мир с уже посчитанным туманом - то же состояние, что после такта."""
    await VisionFacade().refresh_world_vision(world)
    return world


@pytest.fixture
def gate(gameflow: GameFlowFacade) -> PlayerVisionGate:
    return PlayerVisionGate(gameflow_facade=gameflow)


# ==================================================================
# ПРАВИЛО ГЕКСА
# ==================================================================


class TestHexRule:
    async def test_event_inside_the_watch_ring_passes(
        self, gate: PlayerVisionGate, lit_world: WorldState
    ):
        assert gate(ENCOUNTER, {"hex_coords": hex_at(2)})

    async def test_event_beyond_the_ring_is_cut(
        self, gate: PlayerVisionGate, lit_world: WorldState
    ):
        """Стычка в неразведанном секторе игроку не показывается."""
        assert not gate(ENCOUNTER, {"hex_coords": hex_at(9)})

    async def test_hex_can_come_as_a_plain_dict(
        self, gate: PlayerVisionGate, lit_world: WorldState
    ):
        """Нагрузка события может приехать и словарем - гейт разберет оба вида."""
        assert gate(ENCOUNTER, {"hex_coords": {"q": 2, "r": 0, "s": -2}})
        assert not gate(ENCOUNTER, {"hex_coords": {"q": 9, "r": 0, "s": -9}})

    async def test_event_without_a_hex_passes(
        self, gate: PlayerVisionGate, lit_world: WorldState
    ):
        """Экономика собственной державы туманом не закрывается."""
        assert gate("economy.taxes_collected", {"faction_id": "humans"})


# ==================================================================
# ПРАВИЛО АДРЕСАТА
# ==================================================================


class TestObserverRule:
    async def test_own_findings_reach_the_player(
        self, gate: PlayerVisionGate, lit_world: WorldState
    ):
        payload = {"observer_faction_id": "humans", "hex_coords": hex_at(2)}

        assert gate(ARMY_SPOTTED, payload)

    async def test_enemy_findings_stay_with_the_enemy(
        self, gate: PlayerVisionGate, lit_world: WorldState
    ):
        """
        То, что разведал соперник, игрока не касается: иначе по ленте
        читалось бы все чужое поле зрения.
        """
        payload = {"observer_faction_id": "greenskins", "hex_coords": hex_at(2)}

        assert not gate(ARMY_SPOTTED, payload)


# ==================================================================
# ПАРТИЯ ЕЩЕ НЕ НАЧАТА
# ==================================================================


class TestNoActiveParty:
    def test_gate_stays_open_without_a_world(self):
        """Без партии гейт не мешает ничему: игровых событий в этот момент нет."""
        gate = PlayerVisionGate(gameflow_facade=GameFlowFacade())

        assert gate(ENCOUNTER, {"hex_coords": hex_at(9)})

    def test_gate_stays_open_without_a_player(self):
        """Партия-наблюдение: скрывать не от кого."""
        world_state = WorldState()
        world_state.add_faction(build_faction("greenskins", is_player=False))
        facade = GameFlowFacade()
        facade.bind_world_state(world_state)

        gate = PlayerVisionGate(gameflow_facade=facade)

        assert gate(ENCOUNTER, {"hex_coords": hex_at(9)})


# ==================================================================
# МОСТ ЦЕЛИКОМ
# ==================================================================


class TestDispatcherWithGate:
    async def test_dispatcher_drops_what_the_gate_forbids(
        self, gate: PlayerVisionGate, lit_world: WorldState
    ):
        manager = FakeManager()
        dispatcher = EventDispatcher(manager=manager, visibility_gate=gate)

        await dispatcher._forward(ENCOUNTER, hex_coords=hex_at(9))
        await dispatcher._forward(ENCOUNTER, hex_coords=hex_at(2))

        assert manager.events() == [ENCOUNTER]
        assert manager.sent[0].data["hex_coords"] == {"q": 2, "r": 0, "s": -2}

    async def test_dispatcher_without_a_gate_broadcasts_everything(
        self, lit_world: WorldState
    ):
        """Без гейта мост ведет себя как раньше - это нужно тестам и отладке."""
        manager = FakeManager()
        dispatcher = EventDispatcher(manager=manager)

        await dispatcher._forward(ENCOUNTER, hex_coords=hex_at(9))

        assert manager.events() == [ENCOUNTER]

    async def test_broken_gate_does_not_break_the_feed(self, lit_world: WorldState):
        """Сбой гейта рвать ленту не должен: событие уезжает клиенту."""

        def broken_gate(event_key: str, payload: dict) -> bool:
            raise RuntimeError("гейт сломался")

        manager = FakeManager()
        dispatcher = EventDispatcher(manager=manager, visibility_gate=broken_gate)

        await dispatcher._forward(ENCOUNTER, hex_coords=hex_at(9))

        assert manager.events() == [ENCOUNTER]
