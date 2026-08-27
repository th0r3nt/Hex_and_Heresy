"""
Перевод доменных ошибок в статусы HTTP.

Проверяется и таблица соответствий, и то, что она реально срабатывает
на живом обработчике: фасад бросает исключение, клиент видит статус.
"""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from src.back.l01_domain.exceptions.base import DomainError
from src.back.l01_domain.exceptions.chronicler import BattleDossierNotFoundError
from src.back.l01_domain.exceptions.factions import InsufficientResourcesError
from src.back.l01_domain.exceptions.llm import (
    LLMAuthorizationError,
    LLMRequestFailedError,
)
from src.back.l01_domain.exceptions.saves import (
    SaveDuringBattleForbiddenError,
    SaveNotFoundError,
)
from src.back.l01_domain.exceptions.world import NoArmiesLockedForBattleError
from src.back.l02_services.gameflow.guards import ActionForbiddenInCurrentStateError
from src.back.l02_services.gameflow.states import GameState
from src.back.l04_api.http.errors import (
    register_exception_handlers,
    resolve_status_code,
)


# ==================================================================
# ТАБЛИЦА СООТВЕТСТВИЙ
# ==================================================================


@pytest.mark.parametrize(
    "error, expected_status",
    [
        (SaveNotFoundError("quicksave"), status.HTTP_404_NOT_FOUND),
        (BattleDossierNotFoundError("battle-1"), status.HTTP_404_NOT_FOUND),
        (
            InsufficientResourcesError("gold", 100.0, 10.0),
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            SaveDuringBattleForbiddenError(["battle-1"]),
            status.HTTP_409_CONFLICT,
        ),
        (
            ActionForbiddenInCurrentStateError("дипломатия", GameState.MAIN_MENU),
            status.HTTP_409_CONFLICT,
        ),
        (
            NoArmiesLockedForBattleError("battle-1"),
            status.HTTP_409_CONFLICT,
        ),
        (
            LLMAuthorizationError("openrouter", "gpt", "ключ отвергнут"),
            status.HTTP_401_UNAUTHORIZED,
        ),
        (
            LLMRequestFailedError("openrouter", "gpt", "таймаут"),
            status.HTTP_502_BAD_GATEWAY,
        ),
    ],
)
def test_status_matches_error_kind(error: DomainError, expected_status: int):
    assert resolve_status_code(error) == expected_status


def test_authorization_error_wins_over_its_parent():
    """
    LLMAuthorizationError наследует LLMRequestFailedError: если порядок в
    таблице собьется, отказ по ключу превратится в 502 вместо 401.
    """
    error = LLMAuthorizationError("openrouter", "gpt", "ключ отвергнут")

    assert resolve_status_code(error) == status.HTTP_401_UNAUTHORIZED


def test_unmapped_domain_error_is_server_error():
    """
    Ошибка без назначенного статуса - это недосмотр, а не ответ игроку.
    """

    class UnmappedError(DomainError):
        pass

    assert (
        resolve_status_code(UnmappedError("нечто"))
        == status.HTTP_500_INTERNAL_SERVER_ERROR
    )


# ==================================================================
# РАБОТА ОБРАБОТЧИКА В ПРИЛОЖЕНИИ
# ==================================================================


def test_handler_translates_error_thrown_by_endpoint():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise SaveNotFoundError("quicksave")

    with TestClient(app) as client:
        response = client.get("/boom")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    body = response.json()
    assert body["error"] == "SaveNotFoundError"
    assert "quicksave" in body["detail"]
