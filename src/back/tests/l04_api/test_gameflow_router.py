"""
Эндпоинты игрового потока.

Роутер обязан только передать триггер фасаду и вернуть новое состояние;
разрешенность самого перехода - забота конечного автомата.
"""

from fastapi import status
from fastapi.testclient import TestClient

from src.back.l01_domain.world.constants import GlobalEventCategory
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.gameflow.states import GameState
from src.back.tests.l04_api.conftest import FakeContainer


# ==================================================================
# СОСТОЯНИЕ И ПЕРЕХОДЫ
# ==================================================================


def test_state_reports_main_menu_without_party(client: TestClient):
    response = client.get("/api/gameflow/state")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "state": GameState.MAIN_MENU.value,
        "is_party_active": False,
    }


def test_new_game_moves_to_strategic_map(client: TestClient):
    response = client.post("/api/gameflow/new-game")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == GameState.STRATEGIC_MAP.value


def test_state_reports_active_party(client: TestClient, active_party: WorldState):
    response = client.get("/api/gameflow/state")

    assert response.json() == {
        "state": GameState.STRATEGIC_MAP.value,
        "is_party_active": True,
    }


def test_pause_and_resume_return_to_previous_screen(
    client: TestClient, active_party: WorldState
):
    paused = client.post("/api/gameflow/pause")
    assert paused.json()["state"] == GameState.PAUSE.value

    resumed = client.post("/api/gameflow/resume")
    assert resumed.json()["state"] == GameState.STRATEGIC_MAP.value


def test_forbidden_transition_answers_conflict(client: TestClient):
    """Снять с паузы игру, которая на паузе не стоит, нельзя."""
    response = client.post("/api/gameflow/resume")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"] == "InvalidStateTransitionError"


def test_quit_to_menu_unbinds_party(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    """В меню выходят через паузу: с самой карты выход не разрешен."""
    client.post("/api/gameflow/pause")

    response = client.post("/api/gameflow/quit-to-menu")

    assert response.json() == {
        "state": GameState.MAIN_MENU.value,
        "is_party_active": False,
    }
    assert container.gameflow_facade.world_state is None


# ==================================================================
# ОКНО ГЛОБАЛЬНОГО СОБЫТИЯ
# ==================================================================


def test_show_global_event_opens_screen(client: TestClient, active_party: WorldState):
    event = GlobalEvent(
        name="Метеоритный дождь",
        description="С неба падает резонит.",
        category=GlobalEventCategory.LORE_CRISIS,
    )
    active_party.add_event(event)

    response = client.post(
        "/api/gameflow/global-event/show", json={"event_id": event.id}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == GameState.GLOBAL_EVENT_RESOLUTION.value


def test_show_unknown_global_event_answers_not_found(
    client: TestClient, active_party: WorldState
):
    response = client.post(
        "/api/gameflow/global-event/show", json={"event_id": "нет такого"}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ==================================================================
# ТРЕБОВАНИЕ АКТИВНОЙ ПАРТИИ
# ==================================================================


def test_world_dependent_endpoint_requires_started_party(client: TestClient):
    """
    Без начатой партии игровые эндпоинты отвечают конфликтом, а не падают
    на отсутствующем мире.
    """
    response = client.post(
        "/api/gameflow/global-event/show", json={"event_id": "любой"}
    )

    assert response.status_code == status.HTTP_409_CONFLICT
