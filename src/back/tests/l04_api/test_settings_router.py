"""
Экран настроек языковых моделей.

Отдельно проверяется главное правило этого роутера: ключи движутся только
внутрь, наружу уезжает их количество.
"""

from fastapi import status
from fastapi.testclient import TestClient

from src.back.l01_domain.exceptions.llm import (
    LLMKeyMissingError,
    LLMProviderNotConfiguredError,
)
from src.back.l01_domain.llm.models.provider import LLMProviderConfig
from src.back.l03_infrastructure.llm.facade import LLMFacade
from src.back.tests.l04_api.conftest import FakeContainer

SECRET_KEY = "sk-очень-секретный-ключ"


def _config(provider_id: str = "openrouter") -> LLMProviderConfig:
    return LLMProviderConfig(
        id=provider_id,
        title="OpenRouter",
        model="gpt-oss-120b",
        base_url="https://openrouter.ai/api/v1",
    )


# ==================================================================
# ВИТРИНА
# ==================================================================


def test_settings_of_empty_facade_are_empty(
    client: TestClient, container: FakeContainer
):
    container.llm_facade = LLMFacade()

    response = client.get("/api/settings/llm")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "providers": [],
        "active_provider_id": None,
        "fallback_chain": [],
    }


def test_registered_provider_becomes_active_and_visible(
    client: TestClient, container: FakeContainer
):
    container.llm_facade = LLMFacade()

    client.post(
        "/api/settings/llm/providers",
        json={"config": _config().model_dump(mode="json"), "make_active": True},
    )
    response = client.get("/api/settings/llm")

    body = response.json()
    assert body["active_provider_id"] == "openrouter"
    assert body["providers"][0]["title"] == "OpenRouter"
    assert body["providers"][0]["is_active"] is True


def test_keys_are_counted_but_never_returned(
    client: TestClient, container: FakeContainer
):
    facade = LLMFacade()
    facade.register_provider(_config())
    container.llm_facade = facade

    client.put(
        "/api/settings/llm/providers/openrouter/keys",
        json={"keys": [SECRET_KEY, "sk-запасной"]},
    )
    response = client.get("/api/settings/llm")

    assert response.json()["providers"][0]["keys_count"] == 2
    assert SECRET_KEY not in response.text


# ==================================================================
# ОШИБКИ НАСТРОЙКИ
# ==================================================================


def test_activating_unknown_provider_answers_bad_request(
    client: TestClient, container: FakeContainer
):
    container.llm_facade = LLMFacade()

    response = client.post("/api/settings/llm/providers/нет-такого/activate")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == LLMProviderNotConfiguredError.__name__


def test_fallback_chain_of_unknown_providers_is_rejected(
    client: TestClient, container: FakeContainer
):
    facade = LLMFacade()
    facade.register_provider(_config())
    container.llm_facade = facade

    response = client.put(
        "/api/settings/llm/fallback-chain",
        json={"provider_ids": ["openrouter", "нет-такого"]},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert facade.fallback_chain == []


# ==================================================================
# ПРОВЕРКА СВЯЗИ
# ==================================================================


def test_ping_reports_dead_provider_without_raising(
    client: TestClient, container: FakeContainer
):
    """
    Молчащий провайдер - это ответ на вопрос «живой ли он», а не ошибка.
    """

    class SilentFacade(LLMFacade):
        async def ping(self, provider_id=None) -> bool:
            return False

    container.llm_facade = SilentFacade()

    response = client.post("/api/settings/llm/providers/openrouter/ping")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"provider_id": "openrouter", "is_alive": False}


def test_ping_without_keys_is_a_setup_error(
    client: TestClient, container: FakeContainer
):
    """
    Незаполненная настройка - это ошибка запроса, а не «модель молчит»:
    игроку надо показать экран ключей, а не сообщение о сбое сети.
    """
    facade = LLMFacade()
    facade.register_provider(_config())
    container.llm_facade = facade

    response = client.post("/api/settings/llm/providers/openrouter/ping")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["error"] == LLMKeyMissingError.__name__
