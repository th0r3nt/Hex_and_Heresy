"""
Эндпоинты глобальной карты.

Здесь работает настоящий TurnsFacade: проверяется, что приказ игрока
доезжает до мира и меняет его, а не только валидируется схемой.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import BASE_TAX_HQ_PER_LEVEL, TaxPolicyBand
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.tests.l04_api.conftest import FakeContainer


def _army(world_state: WorldState, at: HexCoordinates) -> StrategicArmy:
    army = StrategicArmy(faction_id="humans", name="Первый полк", current_hex=at)
    world_state.add_army(army)
    return army


def _faction(world_state: WorldState) -> Faction:
    faction = Faction(
        id="humans",
        race=FactionRace.HUMANS,
        name="Священная Империя",
        is_player_controlled=True,
        lord=Lord(faction_id="humans", name="Валленштейн", title="Лорд-командующий"),
        headquarters=Headquarters(faction_id="humans", name="Цитадель"),
    )
    world_state.add_faction(faction)
    return faction


# ==================================================================
# МАРШ АРМИЙ
# ==================================================================


def test_march_order_lays_out_the_path(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    army = _army(active_party, HexCoordinates(q=0, r=0, s=0))
    target = HexCoordinates(q=3, r=-3, s=0)

    response = client.post(
        f"/api/strategic/armies/{army.id}/march",
        json={"target_hex": target.model_dump()},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["army_id"] == army.id
    assert body["planned_path"], "маршрут не проложен"
    assert body["planned_path"][-1] == target.model_dump()

    # Приказ отдан именно миру, а не копии
    assert army.target_hex == target
    assert army.planned_path[0] != army.current_hex


def test_march_of_unknown_army_answers_bad_request(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()

    response = client.post(
        "/api/strategic/armies/нет-такой/march",
        json={"target_hex": HexCoordinates(q=1, r=-1, s=0).model_dump()},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "InvalidAssignmentTargetError"


def test_army_locked_by_battle_does_not_march(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    army = _army(active_party, HexCoordinates(q=0, r=0, s=0))
    army.lock_in_tactical_battle()

    response = client.post(
        f"/api/strategic/armies/{army.id}/march",
        json={"target_hex": HexCoordinates(q=2, r=-2, s=0).model_dump()},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert army.planned_path == []


# ==================================================================
# ГЛОБАЛЬНЫЙ ТАКТ
# ==================================================================


def test_turn_advances_the_world(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    ticks_before = active_party.time.total_ticks

    response = client.post("/api/strategic/turn")

    assert response.status_code == status.HTTP_200_OK
    assert "events_report" in response.json()
    assert active_party.time.total_ticks > ticks_before


def test_turn_requires_started_party(
    client: TestClient, container: FakeContainer
):
    container.turns_facade = TurnsFacade()

    response = client.post("/api/strategic/turn")

    assert response.status_code == status.HTTP_409_CONFLICT


# ==================================================================
# РАБОЧИЕ
# ==================================================================


def test_assign_to_unknown_faction_answers_bad_request(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()

    response = client.post(
        "/api/strategic/workers/assign",
        json={
            "squad_id": "отряд-1",
            "faction_id": "нет-такой",
            "building_id": "шахта-1",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "InvalidAssignmentTargetError"


def test_unassign_of_free_squad_is_not_an_error(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    """
    Снять с работ отряд, который нигде не занят, - не ошибка: интерфейс
    может нажать кнопку повторно.
    """
    container.turns_facade = TurnsFacade()

    response = client.post("/api/strategic/workers/отряд-1/unassign")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"] is True


def test_expedition_requires_positive_duration(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()

    response = client.post(
        "/api/strategic/workers/expedition",
        json={
            "squad_id": "отряд-1",
            "faction_id": "humans",
            "target_hex": HexCoordinates(q=2, r=-2, s=0).model_dump(),
            "home_hex": HexCoordinates(q=0, r=0, s=0).model_dump(),
            "mining_duration_ticks": 0,
        },
    )

    assert response.status_code == 422


# ==================================================================
# НАЛОГОВЫЙ ПОЛЗУНОК
# ==================================================================


def test_tax_rate_order_moves_the_slider_in_the_world(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _faction(active_party)

    response = client.put(
        f"/api/strategic/factions/{faction.id}/tax-rate", json={"rate": 1.5}
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["rate"] == 1.5
    assert body["band"] == TaxPolicyBand.PREDATORY.value
    assert body["forecast_income_gold"] == BASE_TAX_HQ_PER_LEVEL * 1.5
    assert body["riot_chance"] == pytest.approx(0.10)

    # Приказ отдан именно миру, а не копии
    assert faction.tax_rate == 1.5


def test_tax_rate_beyond_the_slider_is_rejected(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _faction(active_party)

    response = client.put(
        f"/api/strategic/factions/{faction.id}/tax-rate", json={"rate": 3.0}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "InvalidTaxRateError"
    assert faction.tax_rate == 1.0


def test_tax_rate_of_unknown_faction_answers_not_found(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()

    response = client.put("/api/strategic/factions/нет-такой/tax-rate", json={"rate": 1.0})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"] == "FactionNotFoundError"


def test_tax_rate_is_readable_for_the_slider_tooltip(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _faction(active_party)
    faction.set_tax_rate(0.0)

    response = client.get(f"/api/strategic/factions/{faction.id}/tax-rate")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["band"] == TaxPolicyBand.HOLIDAY.value
    assert body["forecast_income_gold"] == 0.0
    assert body["morale_delta"] == 5.0
