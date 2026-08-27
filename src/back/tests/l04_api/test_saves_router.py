"""
Эндпоинты сохранений.

Роутер отвечает за три вещи: спросить у игрового потока разрешение на
запись, передать команду фасаду и разослать поднятую партию по сервисам.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import status
from fastapi.testclient import TestClient

from src.back.l01_domain.exceptions.saves import SaveNotFoundError
from src.back.l01_domain.world.models.saves import SaveMetadata
from src.back.l01_domain.world.models.state import WorldState
from src.back.tests.l04_api.conftest import FakeContainer, FakeSession


# ==================================================================
# ЗАГЛУШКА ФАСАДА
# ==================================================================


class FakeSavesFacade:
    """Фасад сохранений, запоминающий вызовы вместо работы с базой."""

    def __init__(self, world_state: Optional[WorldState] = None) -> None:
        self._world_state = world_state
        self.saved: list[tuple[str, Optional[str]]] = []
        self.deleted: list[str] = []
        self.missing_save_ids: set[str] = set()

    def _metadata(self, save_id: str, save_name: str) -> SaveMetadata:
        return SaveMetadata(
            save_id=save_id,
            save_name=save_name,
            created_at=datetime.now(timezone.utc),
            total_ticks=0,
            current_day=1,
            current_year=1,
            factions_count=0,
            armies_count=0,
            custom_equipment_count=0,
        )

    async def save_game(
        self, world_state: WorldState, save_name: str, save_id: Optional[str] = None
    ) -> SaveMetadata:
        self.saved.append((save_name, save_id))
        return self._metadata(save_id or "новый-слот", save_name)

    async def quick_save(self, world_state: WorldState) -> SaveMetadata:
        self.saved.append(("Быстрое сохранение", "quicksave"))
        return self._metadata("quicksave", "Быстрое сохранение")

    async def load_game(self, save_id: str) -> FakeSession:
        if save_id in self.missing_save_ids:
            raise SaveNotFoundError(save_id)
        return FakeSession(self._world_state or WorldState())

    async def list_saves(self) -> list[dict[str, Any]]:
        return [{"id": "quicksave", "name": "Быстрое сохранение"}]

    async def has_save(self, save_id: str) -> bool:
        return save_id not in self.missing_save_ids

    async def delete_save(self, save_id: str) -> bool:
        self.deleted.append(save_id)
        return save_id not in self.missing_save_ids


# ==================================================================
# ВИТРИНА
# ==================================================================


def test_list_saves_returns_slots(client: TestClient, container: FakeContainer):
    container.saves_facade = FakeSavesFacade()

    response = client.get("/api/saves")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["items"] == [
        {"id": "quicksave", "name": "Быстрое сохранение"}
    ]


def test_has_save_reports_missing_slot(client: TestClient, container: FakeContainer):
    facade = FakeSavesFacade()
    facade.missing_save_ids.add("нет-такого")
    container.saves_facade = facade

    response = client.get("/api/saves/нет-такого/exists")

    assert response.json() == {"save_id": "нет-такого", "exists": False}


# ==================================================================
# ЗАПИСЬ
# ==================================================================


def test_save_game_writes_named_slot(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = FakeSavesFacade(active_party)
    container.saves_facade = facade

    response = client.post("/api/saves", json={"save_name": "Перед штурмом"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["save_name"] == "Перед штурмом"
    assert facade.saved == [("Перед штурмом", None)]


def test_quick_save_overwrites_its_slot(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = FakeSavesFacade(active_party)
    container.saves_facade = facade

    response = client.post("/api/saves/quick")

    assert response.json()["save_id"] == "quicksave"
    assert facade.saved == [("Быстрое сохранение", "quicksave")]


def test_save_forbidden_during_diplomatic_session(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    """
    Разрешение на запись спрашивается у игрового потока до обращения
    к фасаду: посреди аудиенции сохраняться нельзя.
    """
    container.saves_facade = FakeSavesFacade(active_party)
    client.post(
        "/api/gameflow/audience/open",
        json={"initiator_faction_id": "humans", "target_faction_id": "elfs"},
    )

    response = client.post("/api/saves", json={"save_name": "Посреди аудиенции"})

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"] == "ActionForbiddenInCurrentStateError"


def test_save_from_main_menu_reports_missing_party(
    client: TestClient, container: FakeContainer
):
    """Без начатой партии сохранять нечего - и фасад об этом не спрашивают."""
    facade = FakeSavesFacade()
    container.saves_facade = facade

    response = client.post("/api/saves", json={"save_name": "Из меню"})

    assert response.status_code == status.HTTP_409_CONFLICT
    assert facade.saved == []


def test_save_without_name_is_rejected_by_validation(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.saves_facade = FakeSavesFacade(active_party)

    response = client.post("/api/saves", json={"save_name": ""})

    assert response.status_code == 422


# ==================================================================
# ПОДЪЕМ ПАРТИИ
# ==================================================================


def test_load_game_makes_party_active(client: TestClient, container: FakeContainer):
    world_state = WorldState()
    container.saves_facade = FakeSavesFacade(world_state)

    response = client.post("/api/saves/quicksave/load")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True
    assert container.gameflow_facade.world_state is world_state
    assert len(container.bound_sessions) == 1


def test_load_missing_save_answers_not_found(
    client: TestClient, container: FakeContainer
):
    facade = FakeSavesFacade()
    facade.missing_save_ids.add("нет-такого")
    container.saves_facade = facade

    response = client.post("/api/saves/нет-такого/load")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert container.gameflow_facade.world_state is None


# ==================================================================
# УДАЛЕНИЕ
# ==================================================================


def test_delete_save_reports_missing_slot(
    client: TestClient, container: FakeContainer
):
    facade = FakeSavesFacade()
    facade.missing_save_ids.add("нет-такого")
    container.saves_facade = facade

    response = client.delete("/api/saves/нет-такого")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is False
    assert facade.deleted == ["нет-такого"]
