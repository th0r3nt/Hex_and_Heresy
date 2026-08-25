"""
Тесты сервиса сохранений: подготовки снимка, восстановления сессии и фасада.
"""

from typing import Any, Optional

import pytest

from src.back.l01_domain.army.constants import EquipmentSlot
from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions.saves import (
    EmptySaveNameError,
    SaveDuringBattleForbiddenError,
    SaveNotFoundError,
)
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord, LordArchetype, LordTrait
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.saves.dumper import WorldStateDumper
from src.back.l02_services.saves.facade import QUICK_SAVE_ID, SavesFacade
from src.back.l02_services.saves.loader import WorldStateLoader


class FakeSaveRepository:
    """Хранилище сохранений в памяти, повторяющее контракт SaveGameRepositoryProtocol."""

    def __init__(self) -> None:
        self.rows: dict[str, tuple[str, str]] = {}

    async def save_world_state(self, save_id: str, save_name: str, state: WorldState) -> None:
        # Сериализуем так же, как DatabaseManager, чтобы ловить несериализуемые снимки
        self.rows[save_id] = (save_name, state.model_dump_json())

    async def load_world_state(self, save_id: str) -> Optional[WorldState]:
        row = self.rows.get(save_id)
        if row is None:
            return None
        return WorldState.model_validate_json(row[1])

    async def list_saves(self) -> list[dict[str, Any]]:
        return [{"id": sid, "name": name} for sid, (name, _) in self.rows.items()]

    async def delete_save(self, save_id: str) -> bool:
        return self.rows.pop(save_id, None) is not None


class FakeSessionGameData:
    """Заглушка сессионной геймдаты (в бою - SessionGameDataRepository из l03)."""

    def __init__(self, custom_equipment: list[Equipment]) -> None:
        self.custom_equipment = custom_equipment


class FakeEventBus:
    """Фейковая шина событий для фиксации опубликованных сообщений в тестах."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args, **kwargs) -> None:
        self.events.append((event_name, kwargs))

    def subscribe(self, event_name: str, handler) -> None: ...

    def unsubscribe(self, event_name: str, handler) -> None: ...


def _make_faction() -> Faction:
    return Faction(
        id="humans",
        race=FactionRace.HUMANS,
        name="Священная Империя",
        is_player_controlled=True,
        lord=Lord(
            faction_id="humans",
            name="Валленштейн",
            title="Лорд-командующий",
            archetype=LordArchetype(id="arch_lord", name="Бюрократ", description="..."),
            trait=LordTrait(id="trait_lord", name="Расчетливый", text_fragment="..."),
        ),
        headquarters=Headquarters(faction_id="humans", name="Цитадель"),
    )


def _make_custom_equipment() -> Equipment:
    return Equipment(
        id="wpn_custom_flaming_sword",
        name="Пылающий меч",
        lore="Выкован Оружейником этой партии.",
        slot=EquipmentSlot.WEAPON,
        tier=4,
        is_custom=True,
    )


@pytest.fixture
def repository() -> FakeSaveRepository:
    return FakeSaveRepository()


@pytest.fixture
def event_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def world_state() -> WorldState:
    state = WorldState()
    state.add_faction(_make_faction())
    state.add_army(
        StrategicArmy(faction_id="humans", current_hex=HexCoordinates(q=0, r=0, s=0))
    )
    state.add_custom_equipment(_make_custom_equipment())
    state.time.advance_ticks(5)
    return state


@pytest.fixture
def facade(repository: FakeSaveRepository, event_bus: FakeEventBus) -> SavesFacade:
    return SavesFacade(
        repository=repository,
        gamedata_factory=FakeSessionGameData,
        event_bus=event_bus,
    )


class TestWorldStateDumper:
    def test_metadata_describes_party(self, world_state: WorldState):
        snapshot = WorldStateDumper().prepare(world_state, save_name="  Перед штурмом  ")

        assert snapshot.metadata.save_name == "Перед штурмом"
        assert snapshot.metadata.player_faction_name == "Священная Империя"
        assert snapshot.metadata.factions_count == 1
        assert snapshot.metadata.armies_count == 1
        assert snapshot.metadata.custom_equipment_count == 1
        assert snapshot.metadata.total_ticks == world_state.time.total_ticks

    def test_snapshot_is_detached_from_live_state(self, world_state: WorldState):
        """Партия живет дальше после подготовки снимка - мутации не должны в него протекать."""
        snapshot = WorldStateDumper().prepare(world_state, save_name="Снимок")

        world_state.time.advance_ticks(10)
        world_state.remove_army(next(iter(world_state.armies)))

        assert snapshot.state.time.total_ticks == 5
        assert len(snapshot.state.armies) == 1

    def test_saving_during_battle_is_forbidden(self, world_state: WorldState):
        army_id = next(iter(world_state.armies))
        world_state.lock_armies_for_battle("battle_01", [army_id])

        with pytest.raises(SaveDuringBattleForbiddenError):
            WorldStateDumper().prepare(world_state, save_name="Посреди боя")

    def test_empty_name_is_rejected(self, world_state: WorldState):
        with pytest.raises(EmptySaveNameError):
            WorldStateDumper().prepare(world_state, save_name="   ")


class TestWorldStateLoader:
    async def test_missing_save_raises(self, repository: FakeSaveRepository):
        loader = WorldStateLoader(repository, FakeSessionGameData)

        with pytest.raises(SaveNotFoundError):
            await loader.load("unknown_id")

    def test_stale_battle_locks_are_released(self, world_state: WorldState):
        """Сейв аварийно закрытой сессии не должен навсегда обездвижить армии."""
        army_id = next(iter(world_state.armies))
        world_state.lock_armies_for_battle("battle_01", [army_id])

        loader = WorldStateLoader(FakeSaveRepository(), FakeSessionGameData)
        session = loader.restore_session(world_state)

        assert session.world_state.active_battle_armies == {}
        assert session.world_state.get_army(army_id).is_in_tactical_battle is False

    def test_session_gamedata_receives_custom_equipment(self, world_state: WorldState):
        loader = WorldStateLoader(FakeSaveRepository(), FakeSessionGameData)
        session = loader.restore_session(world_state)

        assert [eq.id for eq in session.gamedata.custom_equipment] == [
            "wpn_custom_flaming_sword"
        ]


class TestSavesFacade:
    async def test_save_and_load_roundtrip(
        self, facade: SavesFacade, world_state: WorldState, event_bus: FakeEventBus
    ):
        metadata = await facade.save_game(world_state, save_name="Перед штурмом")
        session = await facade.load_game(metadata.save_id)

        assert session.world_state.id == world_state.id
        assert session.world_state.time.total_ticks == 5
        assert session.world_state.get_player_faction().name == "Священная Империя"
        assert session.gamedata.custom_equipment[0].id == "wpn_custom_flaming_sword"

        published = [name for name, _ in event_bus.events]
        assert "gameflow.game_saved" in published
        assert "gameflow.game_loaded" in published

    async def test_quick_save_overwrites_single_slot(
        self, facade: SavesFacade, world_state: WorldState, repository: FakeSaveRepository
    ):
        first = await facade.quick_save(world_state)
        world_state.time.advance_ticks(1)
        second = await facade.quick_save(world_state)

        assert first.save_id == second.save_id == QUICK_SAVE_ID
        assert len(repository.rows) == 1

        reloaded = await facade.load_game(QUICK_SAVE_ID)
        assert reloaded.world_state.time.total_ticks == 6

    async def test_named_saves_do_not_collide(
        self, facade: SavesFacade, world_state: WorldState
    ):
        first = await facade.save_game(world_state, save_name="Слот 1")
        second = await facade.save_game(world_state, save_name="Слот 2")

        assert first.save_id != second.save_id
        assert len(await facade.list_saves()) == 2

    async def test_has_save_and_delete(self, facade: SavesFacade, world_state: WorldState):
        metadata = await facade.save_game(world_state, save_name="Временный")

        assert await facade.has_save(metadata.save_id) is True
        assert await facade.delete_save(metadata.save_id) is True
        assert await facade.has_save(metadata.save_id) is False
        assert await facade.delete_save(metadata.save_id) is False

    def test_start_session_needs_no_storage(
        self, facade: SavesFacade, world_state: WorldState
    ):
        """Новая партия получает тот же сессионный репозиторий геймдаты, что и загруженная."""
        session = facade.start_session(world_state)

        assert session.world_state is world_state
        assert session.gamedata.custom_equipment[0].id == "wpn_custom_flaming_sword"
