"""
Роутеры механик: оружейник, мастер игры, дипломатия, летопись.

Все они устроены одинаково - принять схему, дернуть фасад, вернуть ответ,
поэтому проверяется именно это: аргументы доехали до фасада без потерь,
а отказ мастера не превратился в ошибку запроса.
"""

from typing import Any, Optional

from fastapi import status
from fastapi.testclient import TestClient

from src.back.l01_domain.army.constants import EquipmentSlot
from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.exceptions.factions import InsufficientResourcesError
from src.back.l01_domain.world.models.chronicle import ChronicleEntry, RumorEntry
from src.back.l01_domain.world.models.state import WorldState
from src.back.tests.l04_api.conftest import FakeContainer


def _draft() -> Equipment:
    return Equipment(
        id="custom_weapon_powder_blade",
        name="Пороховой клинок",
        lore="Меч с зарядом в навершии.",
        slot=EquipmentSlot.WEAPON,
        tier=3,
        is_custom=True,
    )


# ==================================================================
# ОРУЖЕЙНИК
# ==================================================================


class FakeGunsmithFacade:
    def __init__(
        self, draft: Optional[Equipment], reply: str = "Сделаю."
    ) -> None:
        self._draft = draft
        self._reply = reply
        self.requests: list[str] = []
        self.approved: list[Equipment] = []
        self.approval_error: Optional[Exception] = None

    async def draft_blueprint(
        self, world_state: WorldState, faction_id: str, user_request: str
    ) -> tuple[Optional[Equipment], str]:
        self.requests.append(user_request)
        return self._draft, self._reply

    async def approve_blueprint(
        self, world_state: WorldState, faction_id: str, draft: Equipment
    ) -> None:
        if self.approval_error is not None:
            raise self.approval_error
        self.approved.append(draft)


def test_draft_returns_blueprint(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = FakeGunsmithFacade(_draft())
    container.gunsmith_facade = facade

    response = client.post(
        "/api/gunsmith/blueprints/draft",
        json={"faction_id": "humans", "user_request": "Меч с порохом"},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["is_approved"] is True
    assert body["draft"]["name"] == "Пороховой клинок"
    assert facade.requests == ["Меч с порохом"]


def test_master_refusal_is_an_answer_not_an_error(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    """
    Отказ мастера игрок должен прочитать, а не увидеть красный экран ошибки.
    """
    container.gunsmith_facade = FakeGunsmithFacade(None, reply="Такое я ковать не стану.")

    response = client.post(
        "/api/gunsmith/blueprints/draft",
        json={"faction_id": "humans", "user_request": "Меч из воздуха"},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["is_approved"] is False
    assert body["draft"] is None
    assert body["master_reply"] == "Такое я ковать не стану."


def test_approval_without_resources_answers_bad_request(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = FakeGunsmithFacade(None)
    facade.approval_error = InsufficientResourcesError("gold", 500.0, 10.0, "humans")
    container.gunsmith_facade = facade

    response = client.post(
        "/api/gunsmith/blueprints/approve",
        json={"faction_id": "humans", "draft": _draft().model_dump(mode="json")},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "InsufficientResourcesError"


# ==================================================================
# МАСТЕР ИГРЫ
# ==================================================================


class FakeGameMasterFacade:
    def __init__(self, character: Any = None, reply: str = "Принято.") -> None:
        self._character = character
        self._reply = reply
        self.biographies: list[str] = []
        self.forced_evaluations: list[bool] = []

    async def create_custom_hero(
        self, world_state: WorldState, faction_id: str, biography_text: str
    ) -> tuple[Any, str]:
        self.biographies.append(biography_text)
        return self._character, self._reply

    async def evaluate_world_events(
        self, world_state: WorldState, force: bool = False
    ) -> None:
        self.forced_evaluations.append(force)
        return None


def test_rejected_biography_comes_back_with_explanation(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = FakeGameMasterFacade(None, reply="Слишком мало подробностей.")
    container.game_master_facade = facade

    response = client.post(
        "/api/game-master/heroes",
        json={"faction_id": "humans", "biography_text": "Он был."},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "master_reply": "Слишком мало подробностей.",
        "hero": None,
    }
    assert facade.biographies == ["Он был."]


def test_force_flag_reaches_the_facade(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = FakeGameMasterFacade()
    container.game_master_facade = facade

    client.post("/api/game-master/events/evaluate?force=true")

    assert facade.forced_evaluations == [True]


# ==================================================================
# ДИПЛОМАТИЯ
# ==================================================================


class FakeDiplomacyFacade:
    def __init__(self, tribute: float = 0.0) -> None:
        self._tribute = tribute
        self.payments: list[tuple[str, str]] = []

    async def pay_tribute(
        self, world_state: WorldState, payer_faction_id: str, receiver_faction_id: str
    ) -> float:
        self.payments.append((payer_faction_id, receiver_faction_id))
        return self._tribute


def test_tribute_payment_returns_the_amount(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = FakeDiplomacyFacade(tribute=250.0)
    container.diplomacy_facade = facade

    response = client.post(
        "/api/diplomacy/tribute",
        json={"payer_faction_id": "humans", "receiver_faction_id": "elfs"},
    )

    assert response.json() == {"amount_gold": 250.0}
    assert facade.payments == [("humans", "elfs")]


# ==================================================================
# ЛЕТОПИСЕЦ
# ==================================================================


class FakeChroniclerFacade:
    def __init__(self) -> None:
        self.limits: list[int] = []

    def get_history(self, world_state: WorldState, limit: int) -> list[ChronicleEntry]:
        self.limits.append(limit)
        return [
            ChronicleEntry(
                battle_id="battle-1",
                title="Резня у Пепельного брода",
                body="Их было мало, но они стояли.",
            )
        ]

    def get_rumors(self, world_state: WorldState, limit: int) -> list[RumorEntry]:
        self.limits.append(limit)
        return [RumorEntry(text="В пустошах видели огни.")]


def test_history_page_is_returned(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.chronicler_facade = FakeChroniclerFacade()

    response = client.get("/api/chronicler/history")

    assert response.status_code == status.HTTP_200_OK
    entries = response.json()["entries"]
    assert entries[0]["title"] == "Резня у Пепельного брода"


def test_page_limit_reaches_the_facade(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = FakeChroniclerFacade()
    container.chronicler_facade = facade

    client.get("/api/chronicler/rumors?limit=5")

    assert facade.limits == [5]


def test_absurd_page_limit_is_rejected(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    container.chronicler_facade = FakeChroniclerFacade()

    response = client.get("/api/chronicler/history?limit=100000")

    assert response.status_code == 422
