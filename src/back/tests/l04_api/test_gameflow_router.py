"""
Эндпоинты игрового потока.

Роутер обязан только передать триггер фасаду и вернуть новое состояние;
разрешенность самого перехода - забота конечного автомата.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.world.constants import DifficultyLevel, GlobalEventCategory
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
    """Пустой запрос запускает быструю партию настройками по умолчанию."""
    response = client.post("/api/gameflow/new-game")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["state"] == GameState.STRATEGIC_MAP.value


# ==================================================================
# СТАРТ НОВОЙ ПАРТИИ
# ==================================================================


def test_new_game_returns_a_playable_world(
    client: TestClient, container: FakeContainer
):
    """
    Ответ должен хватать интерфейсу, чтобы нарисовать карту: сид партии, ее
    идентификатор, держава игрока и уже профильтрованный туманом срез мира.
    """
    response = client.post("/api/gameflow/new-game", json={"seed": 777})

    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    world = container.gameflow_facade.world_state

    assert body["seed"] == "777"
    assert body["session_id"] == world.id
    assert body["player_faction_id"] == world.get_player_faction().id
    assert body["is_party_active"] is True
    assert len(body["world"]["factions"]) == len(world.factions)


def test_new_game_binds_the_world_to_the_container(
    client: TestClient, container: FakeContainer
):
    """Мир начатой партии должен разъехаться по сервисам активной игры."""
    client.post("/api/gameflow/new-game")

    assert container.gameflow_facade.world_state is not None
    assert len(container.bound_sessions) == 1


@pytest.mark.parametrize(
    "difficulty, player_gold",
    [
        (DifficultyLevel.EASY, 1500.0),
        (DifficultyLevel.NORMAL, 1000.0),
        (DifficultyLevel.HARD, 600.0),
    ],
)
def test_new_game_respects_the_chosen_difficulty(
    client: TestClient,
    container: FakeContainer,
    difficulty: DifficultyLevel,
    player_gold: float,
):
    response = client.post(
        "/api/gameflow/new-game", json={"difficulty": difficulty.value}
    )

    assert response.status_code == status.HTTP_200_OK

    player = container.gameflow_facade.world_state.get_player_faction()
    assert player.resources["gold"] == player_gold


@pytest.mark.parametrize(
    "player_race, rival_race",
    [
        (FactionRace.HUMANS, FactionRace.GREENSKINS),
        (FactionRace.ELFS, FactionRace.CONGREGATION_OF_THE_METEORITE),
        (FactionRace.BARONIAL_TROOPS, FactionRace.HUMANS),
    ],
)
def test_new_game_accepts_any_pair_of_playable_races(
    client: TestClient,
    container: FakeContainer,
    player_race: FactionRace,
    rival_race: FactionRace,
):
    response = client.post(
        "/api/gameflow/new-game",
        json={
            "player_faction": {"race": player_race.value, "name": "Держава игрока"},
            "rival_faction": {"race": rival_race.value, "name": "Держава соперника"},
        },
    )

    assert response.status_code == status.HTTP_200_OK

    races = {f.race for f in container.gameflow_facade.world_state.factions.values()}
    assert {player_race, rival_race} <= races


def test_new_game_can_leave_baronies_out(
    client: TestClient, container: FakeContainer
):
    response = client.post(
        "/api/gameflow/new-game", json={"include_baronies": False}
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(container.gameflow_facade.world_state.factions) == 2


def test_new_game_rejects_a_race_without_a_realm(client: TestClient):
    """За наемников партию не начать: у них нет ни цитадели, ни правителя."""
    response = client.post(
        "/api/gameflow/new-game",
        json={"player_faction": {"race": FactionRace.MERCENARIES.value, "name": "Роты"}},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "InvalidStartingSetupError"


def test_new_game_rejects_an_unknown_legendary_lord(client: TestClient):
    response = client.post(
        "/api/gameflow/new-game",
        json={
            "player_faction": {
                "race": FactionRace.HUMANS.value,
                "name": "Империя",
                "ruler": {"legendary_lord_id": "lord_hum_no_such_person"},
            }
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"] == "RulerTemplateNotFoundError"


def test_failed_generation_leaves_the_game_in_the_main_menu(
    client: TestClient, container: FakeContainer
):
    """Негодные настройки не должны выводить игру на пустую карту."""
    client.post(
        "/api/gameflow/new-game",
        json={"player_faction": {"race": FactionRace.NEUTRALS.value, "name": "Никто"}},
    )

    assert container.gameflow_facade.current_state == GameState.MAIN_MENU
    assert container.gameflow_facade.world_state is None


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
