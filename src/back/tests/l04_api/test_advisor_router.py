"""
Роутер советника: плановое предложение, очередь открытых окон, ответ игрока
на кнопку и свободный диалог.

Проверяется ровно транспорт: аргументы доехали до фасада без потерь,
молчание советника не превратилось в ошибку, а доменные отказы получили
свой статус.
"""

from typing import Any, Optional

from fastapi import status
from fastapi.testclient import TestClient

from src.back.l01_domain.exceptions.advisor import (
    AdvisorDisabledError,
    AdvisorOptionNotFoundError,
    AdvisorProposalNotFoundError,
)
from src.back.l01_domain.factions.models.advisor import (
    AdvisorAnswer,
    AdvisorDecision,
    AdvisorOption,
    AdvisorOptionKind,
    AdvisorProposal,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.tests.l04_api.conftest import FakeContainer


def _proposal() -> AdvisorProposal:
    return AdvisorProposal(
        id="advp_taxes",
        faction_id="humans",
        title="Казна пуста",
        message="Мой лорд, налоги занижены. Предлагаю поднять сбор на 10%.",
        options=[
            AdvisorOption(id="opt_yes", label="Принять", kind=AdvisorOptionKind.ACCEPT),
            AdvisorOption(
                id="opt_soft", label="Поднять на 5%", kind=AdvisorOptionKind.ADJUST
            ),
        ],
    )


class FakeAdvisorFacade:
    """Советник со скриптованными ответами: роутеру больше ничего не нужно."""

    def __init__(self, proposal: Optional[AdvisorProposal] = None) -> None:
        self._proposal = proposal
        self.offers: list[tuple[str, bool]] = []
        self.answers: list[tuple[str, str, str]] = []
        self.questions: list[str] = []
        self.enabled_calls: list[bool] = []
        self.error: Optional[Exception] = None

    async def offer_proposal(
        self, world_state: WorldState, faction_id: str, force: bool = False
    ) -> Optional[AdvisorProposal]:
        self.offers.append((faction_id, force))
        return self._proposal

    def pending_proposals(self, faction_id: str) -> list[AdvisorProposal]:
        return [self._proposal] if self._proposal is not None else []

    async def answer_proposal(
        self,
        world_state: WorldState,
        proposal_id: str,
        option_id: str,
        player_reply: str = "",
    ) -> AdvisorDecision:
        if self.error is not None:
            raise self.error
        self.answers.append((proposal_id, option_id, player_reply))
        return AdvisorDecision(
            proposal_id=proposal_id,
            option_id=option_id,
            advisor_reply="Будет исполнено, мой лорд.",
        )

    async def ask(
        self, world_state: WorldState, faction_id: str, question: str
    ) -> AdvisorAnswer:
        if self.error is not None:
            raise self.error
        self.questions.append(question)
        return AdvisorAnswer(
            faction_id=faction_id,
            question=question,
            text="Орда в двух переходах от столицы.",
        )

    def set_enabled(self, enabled: bool) -> None:
        self.enabled_calls.append(enabled)


def _bind(container: FakeContainer, facade: Any) -> Any:
    container.advisor_facade = facade
    return facade


# ==================================================================
# ПАССИВНАЯ ИНИЦИАТИВА
# ==================================================================


def test_proposal_reaches_the_interface(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = _bind(container, FakeAdvisorFacade(_proposal()))

    response = client.post(
        "/api/advisor/proposals", json={"faction_id": "humans", "force": True}
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["proposal"]["title"] == "Казна пуста"
    assert [option["label"] for option in body["proposal"]["options"]] == [
        "Принять",
        "Поднять на 5%",
    ]
    assert facade.offers == [("humans", True)]


def test_silent_advisor_is_an_answer_not_an_error(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    """
    Советник промолчал или выключен: интерфейс просто не рисует окно.
    """
    _bind(container, FakeAdvisorFacade(None))

    response = client.post("/api/advisor/proposals", json={"faction_id": "humans"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["proposal"] is None


def test_pending_proposals_are_listed(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    _bind(container, FakeAdvisorFacade(_proposal()))

    response = client.get("/api/advisor/proposals", params={"faction_id": "humans"})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["proposals"]) == 1


def test_advice_without_a_party_is_a_conflict(
    client: TestClient, container: FakeContainer
):
    """Советовать нечего, пока партия не начата."""
    _bind(container, FakeAdvisorFacade(_proposal()))

    response = client.post("/api/advisor/proposals", json={"faction_id": "humans"})

    assert response.status_code == status.HTTP_409_CONFLICT


# ==================================================================
# ОТВЕТ ИГРОКА
# ==================================================================


def test_choice_and_words_of_the_player_reach_the_facade(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = _bind(container, FakeAdvisorFacade(_proposal()))

    response = client.post(
        "/api/advisor/proposals/advp_taxes/answer",
        json={"option_id": "opt_soft", "player_reply": "Хватит и пяти процентов."},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["advisor_reply"] == "Будет исполнено, мой лорд."
    assert facade.answers == [
        ("advp_taxes", "opt_soft", "Хватит и пяти процентов.")
    ]


def test_expired_proposal_answers_not_found(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = _bind(container, FakeAdvisorFacade(_proposal()))
    facade.error = AdvisorProposalNotFoundError("advp_taxes")

    response = client.post(
        "/api/advisor/proposals/advp_taxes/answer", json={"option_id": "opt_yes"}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["error"] == "AdvisorProposalNotFoundError"


def test_unknown_option_answers_bad_request(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = _bind(container, FakeAdvisorFacade(_proposal()))
    facade.error = AdvisorOptionNotFoundError("advp_taxes", "opt_ghost")

    response = client.post(
        "/api/advisor/proposals/advp_taxes/answer", json={"option_id": "opt_ghost"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "AdvisorOptionNotFoundError"


# ==================================================================
# ДИАЛОГОВЫЙ РЕЖИМ
# ==================================================================


def test_question_reaches_the_advisor(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = _bind(container, FakeAdvisorFacade(_proposal()))

    response = client.post(
        "/api/advisor/chat",
        json={
            "faction_id": "humans",
            "question": "Какая армия врага ближе всего к столице?",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["text"] == "Орда в двух переходах от столицы."
    assert facade.questions == ["Какая армия врага ближе всего к столице?"]


def test_empty_question_is_rejected_before_the_facade(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    facade = _bind(container, FakeAdvisorFacade(_proposal()))

    response = client.post(
        "/api/advisor/chat", json={"faction_id": "humans", "question": ""}
    )

    assert response.status_code == 422
    assert facade.questions == []


def test_disabled_advisor_answers_conflict(
    client: TestClient, container: FakeContainer, active_party: WorldState
):
    """Окно, которого игрок не включал, интерфейс открывать не должен."""
    facade = _bind(container, FakeAdvisorFacade(_proposal()))
    facade.error = AdvisorDisabledError()

    response = client.post(
        "/api/advisor/chat", json={"faction_id": "humans", "question": "Что делать?"}
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["error"] == "AdvisorDisabledError"


# ==================================================================
# НАСТРОЙКА
# ==================================================================


def test_advisor_can_be_switched_off(
    client: TestClient, container: FakeContainer
):
    """Переключатель работает и в главном меню: партия для него не нужна."""
    facade = _bind(container, FakeAdvisorFacade(None))

    response = client.put("/api/advisor/enabled", json={"is_enabled": False})

    assert response.status_code == status.HTTP_200_OK
    assert facade.enabled_calls == [False]
