"""
Эндпоинты тактического боя.

Главное, что здесь проверяется: между запросами бой не теряется и не
подменяется копией - приказы копятся в том же объекте, который потом уйдет
в расчет раунда.
"""

from fastapi import status
from fastapi.testclient import TestClient

from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.gameflow.states import GameState
from src.back.tests.l04_api.conftest import FakeContainer

BATTLE_HEX = HexCoordinates(q=0, r=0, s=0)


def _start_battle(client: TestClient, world_state: WorldState) -> dict:
    """Заводит на гексе две враждующие армии и открывает по ним бой."""
    for faction_id in ("humans", "elfs"):
        world_state.add_army(
            StrategicArmy(faction_id=faction_id, current_hex=BATTLE_HEX)
        )

    battle_state = TacticalBattleState()
    response = client.post(
        "/api/tactical/battles",
        json={
            "hex_coordinates": BATTLE_HEX.model_dump(),
            "attacker_faction_id": "humans",
            "defender_faction_id": "elfs",
            "battle_state": battle_state.model_dump(mode="json"),
        },
    )
    assert response.status_code == status.HTTP_200_OK
    return response.json()


# ==================================================================
# НАЧАЛО БОЯ
# ==================================================================


def test_start_battle_switches_mode_and_locks_armies(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    battle = _start_battle(client, active_party)

    assert container.gameflow_facade.current_state == GameState.TACTICAL_COMBAT
    assert active_party.active_battle_armies[battle["id"]]
    assert all(army.is_in_tactical_battle for army in active_party.armies.values())


def test_current_battle_is_kept_between_requests(
    client: TestClient, active_party: WorldState
):
    battle = _start_battle(client, active_party)

    response = client.get("/api/tactical/battles/current")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == battle["id"]


def test_current_battle_without_battle_answers_conflict(
    client: TestClient, active_party: WorldState
):
    response = client.get("/api/tactical/battles/current")

    assert response.status_code == status.HTTP_409_CONFLICT


# ==================================================================
# ПРИКАЗЫ
# ==================================================================


def test_orders_accumulate_in_the_running_battle(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    _start_battle(client, active_party)
    order = {
        "squad_id": "отряд-1",
        "target_cell": CellCoordinates(x=3, y=4).model_dump(),
    }

    response = client.post(
        "/api/tactical/battles/current/orders",
        json={"orders": [order]},
    )

    assert response.status_code == status.HTTP_200_OK
    battle_state = container.gameflow_facade.active_battle_state
    assert [o.squad_id for o in battle_state.pending_orders] == ["отряд-1"]


def test_new_orders_replace_previous_ones(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    _start_battle(client, active_party)

    def send(squad_id: str, replace: bool):
        return client.post(
            "/api/tactical/battles/current/orders",
            json={
                "orders": [
                    {
                        "squad_id": squad_id,
                        "target_cell": CellCoordinates(x=1, y=1).model_dump(),
                    }
                ],
                "replace_pending": replace,
            },
        )

    send("отряд-1", replace=True)
    send("отряд-2", replace=True)

    battle_state = container.gameflow_facade.active_battle_state
    assert [o.squad_id for o in battle_state.pending_orders] == ["отряд-2"]


def test_orders_can_be_added_to_previous_ones(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    _start_battle(client, active_party)

    for squad_id in ("отряд-1", "отряд-2"):
        client.post(
            "/api/tactical/battles/current/orders",
            json={
                "orders": [
                    {
                        "squad_id": squad_id,
                        "target_cell": CellCoordinates(x=1, y=1).model_dump(),
                    }
                ],
                "replace_pending": False,
            },
        )

    battle_state = container.gameflow_facade.active_battle_state
    assert [o.squad_id for o in battle_state.pending_orders] == ["отряд-1", "отряд-2"]


# ==================================================================
# ЗАВЕРШЕНИЕ БОЯ
# ==================================================================


def test_finish_battle_returns_to_map_and_frees_armies(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    battle = _start_battle(client, active_party)

    response = client.post(
        "/api/tactical/battles/current/finish",
        json={"victor_faction_id": "humans"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert container.gameflow_facade.current_state == GameState.STRATEGIC_MAP
    assert battle["id"] not in active_party.active_battle_armies
    assert not any(army.is_in_tactical_battle for army in active_party.armies.values())
