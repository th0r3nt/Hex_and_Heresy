"""
Тесты фасада LLM: регистрация провайдеров, ключи, маршрутизация запросов
по цепочке фоллбэков и освобождение ресурсов.
"""

from typing import Any, Dict, List

import pytest
from pydantic import BaseModel

from src.back.l01_domain.exceptions import (
    LLMKeyMissingError,
    LLMProviderNotConfiguredError,
    LLMRequestFailedError,
)
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l03_infrastructure.llm import facade as facade_module
from src.back.l03_infrastructure.llm.facade import LLMFacade


class Verdict(BaseModel):
    """Схема структурированного ответа для тестов фасада."""

    decision: str = "ждать"


class ScriptedExecutor:
    """Заглушка исполнителя: отвечает или падает по сценарию, привязанному к провайдеру."""

    behaviors: Dict[str, Any] = {}
    created: Dict[str, "ScriptedExecutor"] = {}
    attempts: List[str] = []

    def __init__(self, config, client) -> None:
        self.config = config
        self.client = client
        self.text_calls: List[Dict[str, Any]] = []
        self.structured_calls: List[Dict[str, Any]] = []
        ScriptedExecutor.created[config.id] = self

    def _resolve(self, default: Any) -> Any:
        ScriptedExecutor.attempts.append(self.config.id)
        behavior = ScriptedExecutor.behaviors.get(self.config.id, default)
        if isinstance(behavior, BaseException):
            raise behavior
        return behavior

    async def generate_text(self, **kwargs: Any) -> str:
        self.text_calls.append(kwargs)
        return self._resolve(f"текст от {self.config.id}")

    async def generate_structured(self, **kwargs: Any) -> Any:
        self.structured_calls.append(kwargs)
        return self._resolve(kwargs["response_model"]())


@pytest.fixture(autouse=True)
def scripted_executors(monkeypatch: pytest.MonkeyPatch):
    """Подменяет настоящий LLMExecutor на скриптованный."""
    ScriptedExecutor.behaviors = {}
    ScriptedExecutor.created = {}
    ScriptedExecutor.attempts = []
    monkeypatch.setattr(facade_module, "LLMExecutor", ScriptedExecutor)
    return ScriptedExecutor


@pytest.fixture
def facade() -> LLMFacade:
    return LLMFacade()


@pytest.fixture
def cloud(llm_fakes):
    return llm_fakes.config(id="cloud", title="Облако", model="cloud-model")


@pytest.fixture
def local(llm_fakes):
    return llm_fakes.config(
        id="local",
        title="Локальная модель",
        model="local-model",
        base_url="localhost:1234/v1",
        requires_api_key=False,
    )


class TestContract:
    def test_facade_implements_llm_client_protocol(self, facade: LLMFacade):
        assert isinstance(facade, LLMClientProtocol)


class TestRegistration:
    def test_first_provider_becomes_active(self, facade: LLMFacade, cloud, local):
        facade.register_provider(cloud)
        facade.register_provider(local)

        assert facade._active_id == "cloud"

    def test_make_active_switches_provider(self, facade: LLMFacade, cloud, local):
        facade.register_provider(cloud)
        facade.register_provider(local, make_active=True)

        assert facade._active_id == "local"

    def test_unknown_provider_cannot_be_activated(self, facade: LLMFacade, cloud):
        facade.register_provider(cloud)

        with pytest.raises(LLMProviderNotConfiguredError):
            facade.set_active_provider("ghost")

        assert facade._active_id == "cloud"

    def test_known_provider_is_activated(self, facade: LLMFacade, cloud, local):
        facade.register_provider(cloud)
        facade.register_provider(local)

        facade.set_active_provider("local")

        assert facade._active_id == "local"

    def test_fallback_chain_rejects_unknown_providers(self, facade: LLMFacade, cloud):
        facade.register_provider(cloud)

        with pytest.raises(LLMProviderNotConfiguredError):
            facade.set_fallback_chain(["cloud", "ghost"])

        assert facade._fallback_ids == []

    async def test_reregistration_rebuilds_executor(self, facade: LLMFacade, local, llm_fakes):
        facade.register_provider(local)
        await facade.generate_text(system_prompt="s", user_prompt="u")
        first = facade._executors["local"]

        facade.register_provider(llm_fakes.config(id="local", title="Т", model="new-model"))
        await facade.generate_text(system_prompt="s", user_prompt="u")

        assert facade._executors["local"] is not first
        assert facade._executors["local"].config.model == "new-model"

    async def test_new_keys_rebuild_executor(self, facade: LLMFacade, cloud):
        facade.register_provider(cloud)
        facade.set_api_keys("cloud", ["key-one"])
        await facade.generate_text(system_prompt="s", user_prompt="u")
        first = facade._executors["cloud"]

        facade.set_api_keys("cloud", ["key-two"])
        await facade.generate_text(system_prompt="s", user_prompt="u")

        assert facade._executors["cloud"] is not first
        assert facade._rotators["cloud"].keys == ["key-two"]

    def test_keys_are_handed_to_a_fresh_rotator(self, facade: LLMFacade, cloud):
        facade.register_provider(cloud)

        facade.set_api_keys("cloud", ["  key-one  ", ""])

        assert facade._rotators["cloud"].keys == ["key-one"]

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Баг: set_api_keys с пустым списком для незарегистрированного провайдера "
            "читает поле у класса LLMProviderConfig и падает с AttributeError"
        ),
    )
    def test_empty_keys_for_unknown_provider_do_not_crash(self, facade: LLMFacade):
        facade.set_api_keys("ghost", [])

        assert facade._rotators["ghost"].total_keys() == 0


class TestRouting:
    async def test_active_provider_serves_the_request(self, facade: LLMFacade, cloud, local):
        facade.register_provider(cloud)
        facade.register_provider(local)
        facade.set_api_keys("cloud", ["key-one"])

        result = await facade.generate_text(
            system_prompt="Ты — лорд.", user_prompt="Реши.", temperature=0.4, max_tokens=100
        )

        assert result == "текст от cloud"
        assert ScriptedExecutor.attempts == ["cloud"]
        assert ScriptedExecutor.created["cloud"].text_calls[0] == {
            "system_prompt": "Ты — лорд.",
            "user_prompt": "Реши.",
            "temperature": 0.4,
            "max_tokens": 100,
        }

    async def test_structured_request_carries_the_schema(self, facade: LLMFacade, local):
        facade.register_provider(local)

        verdict = await facade.generate_structured(
            system_prompt="s", user_prompt="u", response_model=Verdict, temperature=0.2
        )

        assert isinstance(verdict, Verdict)
        call = ScriptedExecutor.created["local"].structured_calls[0]
        assert call["response_model"] is Verdict
        assert call["temperature"] == 0.2

    async def test_failed_provider_hands_over_to_fallback(
        self, facade: LLMFacade, cloud, local
    ):
        facade.register_provider(cloud, make_active=True)
        facade.register_provider(local)
        facade.set_api_keys("cloud", ["key-one"])
        facade.set_fallback_chain(["local"])
        ScriptedExecutor.behaviors["cloud"] = LLMRequestFailedError(
            "cloud", "cloud-model", "провайдер лег"
        )

        result = await facade.generate_text(system_prompt="s", user_prompt="u")

        assert result == "текст от local"
        assert ScriptedExecutor.attempts == ["cloud", "local"]

    async def test_active_provider_is_not_tried_twice(self, facade: LLMFacade, cloud, local):
        facade.register_provider(cloud, make_active=True)
        facade.register_provider(local)
        facade.set_api_keys("cloud", ["key-one"])
        facade.set_fallback_chain(["cloud", "local"])
        ScriptedExecutor.behaviors["cloud"] = LLMRequestFailedError(
            "cloud", "cloud-model", "провайдер лег"
        )

        await facade.generate_text(system_prompt="s", user_prompt="u")

        assert ScriptedExecutor.attempts == ["cloud", "local"]

    async def test_last_error_wins_when_everyone_fails(self, facade: LLMFacade, cloud, local):
        facade.register_provider(cloud, make_active=True)
        facade.register_provider(local)
        facade.set_api_keys("cloud", ["key-one"])
        facade.set_fallback_chain(["local"])
        local_error = LLMRequestFailedError("local", "local-model", "и локальная легла")
        ScriptedExecutor.behaviors["cloud"] = LLMRequestFailedError(
            "cloud", "cloud-model", "провайдер лег"
        )
        ScriptedExecutor.behaviors["local"] = local_error

        with pytest.raises(LLMRequestFailedError) as exc_info:
            await facade.generate_text(system_prompt="s", user_prompt="u")

        assert exc_info.value is local_error

    async def test_unexpected_error_is_not_swallowed_by_fallback(
        self, facade: LLMFacade, cloud, local
    ):
        facade.register_provider(cloud, make_active=True)
        facade.register_provider(local)
        facade.set_api_keys("cloud", ["key-one"])
        facade.set_fallback_chain(["local"])
        ScriptedExecutor.behaviors["cloud"] = RuntimeError("баг в коде")

        with pytest.raises(RuntimeError):
            await facade.generate_text(system_prompt="s", user_prompt="u")

        assert ScriptedExecutor.attempts == ["cloud"]

    async def test_provider_without_keys_is_skipped(self, facade: LLMFacade, cloud, local):
        facade.register_provider(cloud, make_active=True)  # требует ключ, но ключей нет
        facade.register_provider(local)
        facade.set_fallback_chain(["local"])

        result = await facade.generate_text(system_prompt="s", user_prompt="u")

        assert result == "текст от local"
        assert ScriptedExecutor.attempts == ["local"]

    async def test_missing_keys_are_reported_when_nobody_can_answer(
        self, facade: LLMFacade, cloud
    ):
        facade.register_provider(cloud)

        with pytest.raises(LLMKeyMissingError) as exc_info:
            await facade.generate_text(system_prompt="s", user_prompt="u")

        assert exc_info.value.provider_id == "cloud"

    async def test_keyless_provider_gets_an_empty_rotator(self, facade: LLMFacade, local):
        facade.register_provider(local)

        assert await facade.generate_text(system_prompt="s", user_prompt="u") == "текст от local"
        assert facade._rotators["local"].total_keys() == 0

    async def test_empty_configuration_is_an_explicit_error(self, facade: LLMFacade):
        with pytest.raises(LLMProviderNotConfiguredError):
            await facade.generate_text(system_prompt="s", user_prompt="u")

    async def test_executor_is_built_once_and_reused(self, facade: LLMFacade, local):
        facade.register_provider(local)

        await facade.generate_text(system_prompt="s", user_prompt="u")
        first = facade._executors["local"]
        await facade.generate_text(system_prompt="s", user_prompt="u")

        assert facade._executors["local"] is first
        assert len(first.text_calls) == 2


class TestLifecycle:
    async def test_close_all_releases_clients(self, facade: LLMFacade, local):
        facade.register_provider(local)
        await facade.generate_text(system_prompt="s", user_prompt="u")
        assert facade._clients

        await facade.close_all()

        assert facade._clients == {}
        assert facade._executors == {}

    async def test_close_all_is_safe_on_untouched_facade(self, facade: LLMFacade):
        await facade.close_all()

        assert facade._clients == {}

    async def test_facade_works_again_after_close(self, facade: LLMFacade, local):
        facade.register_provider(local)
        await facade.generate_text(system_prompt="s", user_prompt="u")
        await facade.close_all()

        assert await facade.generate_text(system_prompt="s", user_prompt="u") == "текст от local"
