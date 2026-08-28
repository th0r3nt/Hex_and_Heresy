"""
Эндпоинты глобальной карты.

Здесь работает настоящий TurnsFacade: проверяется, что приказ игрока
доезжает до мира и меняет его, а не только валидируется схемой.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import (
    BASE_TAX_HQ_PER_LEVEL,
    MAX_BORDER_TOWN_ALLIED_LANDS,
    MAX_BORDER_TOWN_LEVEL,
    MAX_STATIONED_GARRISON_SQUADS,
    ResourceType,
    TaxPolicyBand,
)
from src.back.l01_domain.factions.models.border_town import BorderTown
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.garrison import Garrison
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    hex_neighbors,
    hex_zone_id,
)
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


# ==================================================================
# ГАРНИЗОНЫ ЗЕМЕЛЬ
# ==================================================================


def _garrison(world_state: WorldState, faction: Faction, at: HexCoordinates) -> Garrison:
    """Ставит на гекс готовый гарнизон, как это делает такт."""
    garrison = Garrison(
        zone_id=hex_zone_id(at), faction_id=faction.id, hex_coordinates=at
    )
    world_state.add_garrison(garrison)
    return garrison


def _garrison_squad() -> Squad:
    """Регулярный отряд, который игрок может оставить за стенами."""
    return Squad.create_new(
        archetype=UnitArchetype(
            id="unit_test_guard",
            race=FactionRace.HUMANS,
            faction_id="humans",
            name="Городская стража",
            tier=1,
            default_unit_count=100,
            base_stats=BaseUnitStats(max_hp=20.0),
        )
    )


def test_garrison_state_is_readable(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _faction(active_party)
    capital = HexCoordinates(q=0, r=0, s=0)
    garrison = _garrison(active_party, faction, capital)
    garrison.sync_militia_capacity(level=1, recruit=_garrison_squad)

    response = client.get(f"/api/strategic/garrisons/{garrison.zone_id}")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["zone_id"] == garrison.zone_id
    assert len(body["militia_squads"]) == 2
    assert body["stationed_squads"] == []
    assert body["free_stationed_slots"] == MAX_STATIONED_GARRISON_SQUADS


def test_garrison_of_unknown_land_answers_not_found(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()

    response = client.get("/api/strategic/garrisons/99,99")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"] == "GarrisonNotFoundError"


def test_station_endpoint_moves_the_squad_behind_the_walls(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _faction(active_party)
    capital = HexCoordinates(q=0, r=0, s=0)
    garrison = _garrison(active_party, faction, capital)
    army = _army(active_party, capital)
    squad = _garrison_squad()
    army.add_squad(squad)

    response = client.post(
        f"/api/strategic/garrisons/{garrison.zone_id}/station",
        json={"army_id": army.id, "squad_id": squad.id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["stationed_squads"]) == 1

    # Приказ отдан именно миру, а не копии
    assert garrison.stationed_squads == [squad]
    assert army.squads == []


def test_unstation_endpoint_returns_the_squad_to_the_army(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _faction(active_party)
    capital = HexCoordinates(q=0, r=0, s=0)
    garrison = _garrison(active_party, faction, capital)
    army = _army(active_party, capital)
    squad = _garrison_squad()
    garrison.station_squad(squad)

    response = client.post(
        f"/api/strategic/garrisons/{garrison.zone_id}/unstation",
        json={"army_id": army.id, "squad_id": squad.id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["stationed_squads"] == []
    assert army.squads == [squad]


def test_station_beyond_the_limit_answers_conflict(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _faction(active_party)
    capital = HexCoordinates(q=0, r=0, s=0)
    garrison = _garrison(active_party, faction, capital)
    for _ in range(MAX_STATIONED_GARRISON_SQUADS):
        garrison.station_squad(_garrison_squad())

    army = _army(active_party, capital)
    extra = _garrison_squad()
    army.add_squad(extra)

    response = client.post(
        f"/api/strategic/garrisons/{garrison.zone_id}/station",
        json={"army_id": army.id, "squad_id": extra.id},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"] == "GarrisonCapacityExceededError"
    assert army.squads == [extra], "отказ не должен терять отряд"


def test_station_during_the_assault_is_refused(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _faction(active_party)
    capital = HexCoordinates(q=0, r=0, s=0)
    garrison = _garrison(active_party, faction, capital)
    garrison.is_locked_in_battle = True

    army = _army(active_party, capital)
    squad = _garrison_squad()
    army.add_squad(squad)

    response = client.post(
        f"/api/strategic/garrisons/{garrison.zone_id}/station",
        json={"army_id": army.id, "squad_id": squad.id},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"] == "GarrisonLockedInBattleError"


def test_distant_army_cannot_use_the_garrison(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _faction(active_party)
    garrison = _garrison(active_party, faction, HexCoordinates(q=0, r=0, s=0))
    army = _army(active_party, HexCoordinates(q=5, r=-5, s=0))
    squad = _garrison_squad()
    army.add_squad(squad)

    response = client.post(
        f"/api/strategic/garrisons/{garrison.zone_id}/station",
        json={"army_id": army.id, "squad_id": squad.id},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"] == "GarrisonRotationForbiddenError"


# ==================================================================
# ПОГРАНИЧНЫЕ ГОРОДА
# ==================================================================


def _rich_faction(world_state: WorldState) -> Faction:
    """Фракция, которой хватит казны и на город, и на его земли."""
    faction = _faction(world_state)
    faction.resources[ResourceType.GOLD] = 5000.0
    faction.resources[ResourceType.MATERIAL] = 5000.0
    faction.resources[ResourceType.FOOD] = 5000.0
    return faction


def test_border_town_is_founded_on_a_free_hex(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _rich_faction(active_party)
    target = HexCoordinates(q=0, r=0, s=0)

    response = client.post(
        "/api/strategic/border-towns",
        json={
            "faction_id": faction.id,
            "target_hex": target.model_dump(),
            "name": "Врата висельников",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["name"] == "Врата висельников"
    assert body["level"] == 1
    assert body["building_slots"] == 2
    assert body["free_land_slots"] == MAX_BORDER_TOWN_ALLIED_LANDS

    # Приказ доехал именно до мира, а не до копии
    assert len(faction.border_towns) == 1
    assert faction.border_towns[0].center_hex == target


def test_town_on_an_occupied_hex_answers_conflict(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _rich_faction(active_party)
    faction.capital_hex = HexCoordinates(q=0, r=0, s=0)

    response = client.post(
        "/api/strategic/border-towns",
        json={
            "faction_id": faction.id,
            "target_hex": faction.capital_hex.model_dump(),
            "name": "Второй престол",
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"] == "InvalidSettlementPlacementError"
    assert faction.border_towns == []


def test_founding_without_gold_answers_bad_request(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _faction(active_party)

    response = client.post(
        "/api/strategic/border-towns",
        json={
            "faction_id": faction.id,
            "target_hex": HexCoordinates(q=0, r=0, s=0).model_dump(),
            "name": "Город на честном слове",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "InsufficientResourcesError"
    assert faction.border_towns == []


def test_border_town_is_upgraded(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _rich_faction(active_party)
    town = BorderTown(
        faction_id=faction.id,
        name="Врата висельников",
        center_hex=HexCoordinates(q=0, r=0, s=0),
    )
    faction.add_border_town(town)

    response = client.post(
        f"/api/strategic/border-towns/{town.id}/upgrade",
        json={"faction_id": faction.id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["level"] == 2
    assert town.level == 2


def test_upgrade_beyond_the_ceiling_answers_conflict(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _rich_faction(active_party)
    town = BorderTown(
        faction_id=faction.id,
        name="Врата висельников",
        center_hex=HexCoordinates(q=0, r=0, s=0),
        level=MAX_BORDER_TOWN_LEVEL,
    )
    faction.add_border_town(town)

    response = client.post(
        f"/api/strategic/border-towns/{town.id}/upgrade",
        json={"faction_id": faction.id},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"] == "BorderTownMaxLevelReachedError"


def test_unknown_town_answers_not_found(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _rich_faction(active_party)

    response = client.post(
        "/api/strategic/border-towns/нет-такого/upgrade",
        json={"faction_id": faction.id},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"] == "BorderTownNotFoundError"


def test_adjacent_land_is_claimed_with_a_hall(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _rich_faction(active_party)
    center = HexCoordinates(q=0, r=0, s=0)
    town = BorderTown(faction_id=faction.id, name="Врата висельников", center_hex=center)
    faction.add_border_town(town)
    land = hex_neighbors(center)[0]

    response = client.post(
        f"/api/strategic/border-towns/{town.id}/claim-land",
        json={"faction_id": faction.id, "target_hex": land.model_dump()},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["free_land_slots"] == MAX_BORDER_TOWN_ALLIED_LANDS - 1
    assert faction.get_regional_hall(hex_zone_id(land)) is not None


def test_distant_land_answers_bad_request(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _rich_faction(active_party)
    town = BorderTown(
        faction_id=faction.id,
        name="Врата висельников",
        center_hex=HexCoordinates(q=0, r=0, s=0),
    )
    faction.add_border_town(town)

    response = client.post(
        f"/api/strategic/border-towns/{town.id}/claim-land",
        json={
            "faction_id": faction.id,
            "target_hex": HexCoordinates(q=3, r=-3, s=0).model_dump(),
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "HexNotAdjacentToTownError"
    assert town.claimed_hexes == []


def test_faction_border_towns_are_listed(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    faction = _rich_faction(active_party)
    faction.add_border_town(
        BorderTown(
            faction_id=faction.id,
            name="Врата висельников",
            center_hex=HexCoordinates(q=0, r=0, s=0),
        )
    )
    faction.add_border_town(
        BorderTown(
            faction_id=faction.id,
            name="Пепельный острог",
            center_hex=HexCoordinates(q=2, r=-2, s=0),
        )
    )

    response = client.get(f"/api/strategic/factions/{faction.id}/border-towns")

    assert response.status_code == status.HTTP_200_OK
    assert [town["name"] for town in response.json()] == [
        "Врата висельников",
        "Пепельный острог",
    ]


# ==================================================================
# СУДЬБА ПОБЕЖДЕННОГО ПОГРАНИЧНОГО ГОРОДА
# ==================================================================


def _defeated_town(world_state: WorldState) -> tuple[Faction, BorderTown, StrategicArmy]:
    """
    Готовая обстановка после штурма: город людей с пустым гарнизоном и
    орочья армия на его гексе.
    """
    owner = _rich_faction(world_state)
    center = HexCoordinates(q=2, r=-4, s=2)

    town = BorderTown(faction_id=owner.id, name="Врата висельников", center_hex=center)
    town.register_investment({ResourceType.GOLD: 1000.0})
    owner.add_border_town(town)
    owner.gain_zone(town.zone_id)

    world_state.add_garrison(
        Garrison(zone_id=town.zone_id, faction_id=owner.id, hex_coordinates=center)
    )

    conqueror = Faction(
        id="greenskins",
        race=FactionRace.GREENSKINS,
        name="Орда Ржавых Клыков",
        lord=Lord(faction_id="greenskins", name="Гром", title="Вождь"),
        headquarters=Headquarters(faction_id="greenskins", name="Шатер Вождя"),
    )
    world_state.add_faction(conqueror)

    horde = StrategicArmy(faction_id=conqueror.id, name="Орда", current_hex=center)
    world_state.add_army(horde)

    return owner, town, horde


def test_resolve_endpoint_starts_the_operation(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    _, town, horde = _defeated_town(active_party)

    response = client.post(
        f"/api/strategic/border-towns/{town.id}/resolve",
        json={"army_id": horde.id, "resolution_type": "raze"},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["operation_id"]
    assert body["resolution_type"] == "raze"
    assert body["ticks_remaining"] == 3
    assert body["estimated_loot"]["gold"] == 500.0

    # Приказ доехал именно до мира, а не до копии
    assert horde.is_busy_with_operation
    assert active_party.get_town_operation(town.id) is not None


def test_ignored_town_answers_without_an_operation(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    _, town, horde = _defeated_town(active_party)

    response = client.post(
        f"/api/strategic/border-towns/{town.id}/resolve",
        json={"army_id": horde.id, "resolution_type": "ignore"},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["operation_id"] is None
    assert body["ticks_remaining"] == 0
    assert body["estimated_loot"] == {}
    assert not horde.is_busy_with_operation
    assert active_party.border_town_operations == {}


def test_resolve_of_unknown_town_answers_not_found(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    _, _, horde = _defeated_town(active_party)

    response = client.post(
        "/api/strategic/border-towns/нет-такого/resolve",
        json={"army_id": horde.id, "resolution_type": "raze"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"] == "BorderTownNotFoundError"


def test_resolve_of_a_town_still_holding_answers_conflict(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    _, town, horde = _defeated_town(active_party)
    active_party.get_garrison(town.zone_id).stationed_squads.append(_garrison_squad())

    response = client.post(
        f"/api/strategic/border-towns/{town.id}/resolve",
        json={"army_id": horde.id, "resolution_type": "pillage"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"] == "BorderTownResolutionInvalidError"
    assert not horde.is_busy_with_operation


def test_second_operation_on_the_same_town_answers_conflict(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    owner, town, horde = _defeated_town(active_party)
    second_horde = StrategicArmy(
        faction_id="greenskins", name="Вторая орда", current_hex=town.center_hex
    )
    active_party.add_army(second_horde)

    client.post(
        f"/api/strategic/border-towns/{town.id}/resolve",
        json={"army_id": horde.id, "resolution_type": "raze"},
    )
    response = client.post(
        f"/api/strategic/border-towns/{town.id}/resolve",
        json={"army_id": second_horde.id, "resolution_type": "pillage"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"] == "BorderTownOperationInProgressError"


def test_unknown_resolution_type_is_rejected_by_the_schema(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    _, town, horde = _defeated_town(active_party)

    response = client.post(
        f"/api/strategic/border-towns/{town.id}/resolve",
        json={"army_id": horde.id, "resolution_type": "продать в рабство"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_operation_progress_is_readable(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    _, town, horde = _defeated_town(active_party)
    client.post(
        f"/api/strategic/border-towns/{town.id}/resolve",
        json={"army_id": horde.id, "resolution_type": "occupy"},
    )

    response = client.get(f"/api/strategic/border-towns/{town.id}/operation")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["resolution_type"] == "occupy"
    assert body["ticks_remaining"] == 2
    assert body["estimated_loot"]["gold"] == 250.0


def test_untouched_town_reports_an_idle_operation(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.turns_facade = TurnsFacade()
    _, town, _ = _defeated_town(active_party)

    response = client.get(f"/api/strategic/border-towns/{town.id}/operation")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["operation_id"] is None
    assert body["resolution_type"] == "ignore"
    assert body["ticks_remaining"] == 0
