"""
Тесты фасада LLM: реестр провайдеров, цепочка запасных и проксирование ключей.
"""

import json

import pytest

from src.back.l01_domain.exceptions import (
    LLMKeyMissingError,
    LLMProviderNotConfiguredError,
    LLMRateLimitError,
    LLMRequestFailedError,
)
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l03_infrastructure.llm.client import LLMProviderConfig
from src.back.l03_infrastructure.llm.keys.manager import ApiKeyManager
from src.back.l03_infrastructure.llm.manager import LLMManager
from src.back.tests.l03_infrastructure.llm.conftest import WarCouncilDecision


class ScriptedClient(LLMClientProtocol):
    """Клиент-дублер: отвечает заготовкой или падает заданной ошибкой."""

    def __init__(self, provider_id: str, answer=None, error: Exception = None) -> None:
        self.provider_id = provider_id
        self.answer = answer
        self.error = error
        self.calls = 0

    async def generate_text(self, system_prompt, user_prompt, temperature=0.8, max_tokens=None):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.answer

    async def generate_structured(
        self, system_prompt, user_prompt, response_model, temperature=0.6
    ):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return response_model.model_validate_json(json.dumps(self.answer))


class ClientRegistry:
    """Фабрика клиентов для менеджера: раздает заранее подготовленные дублеры."""

    def __init__(self, **clients: ScriptedClient) -> None:
        self.clients = clients
        self.built: list[str] = []

    def __call__(self, config: LLMProviderConfig, keys: ApiKeyManager) -> LLMClientProtocol:
        self.built.append(config.id)
        return self.clients[config.id]


def _provider(provider_id: str, requires_key: bool = True) -> LLMProviderConfig:
    return LLMProviderConfig(
        id=provider_id,
        title=provider_id,
        model=f"model-{provider_id}",
        requires_api_key=requires_key,
    )


class TestProviderRegistry:
    def test_first_registered_provider_becomes_active(self):
        manager = LLMManager()

        manager.register_provider(_provider("cloud"))
        manager.register_provider(_provider("local", requires_key=False))

        assert manager.active_provider.id == "cloud"

    def test_active_provider_can_be_switched(self):
        manager = LLMManager()
        manager.register_provider(_provider("cloud"))
        manager.register_provider(_provider("local", requires_key=False))

        manager.set_active_provider("local")

        assert manager.active_provider.id == "local"

    def test_switching_to_unknown_provider_raises(self):
        manager = LLMManager()

        with pytest.raises(LLMProviderNotConfiguredError):
            manager.set_active_provider("ghost")

    def test_removing_active_provider_promotes_another(self):
        manager = LLMManager()
        manager.register_provider(_provider("cloud"))
        manager.register_provider(_provider("local", requires_key=False))

        manager.remove_provider("cloud")

        assert manager.active_provider.id == "local"
        assert [config.id for config in manager.list_providers()] == ["local"]

    def test_unknown_provider_in_fallback_chain_raises(self):
        manager = LLMManager()
        manager.register_provider(_provider("cloud"))

        with pytest.raises(LLMProviderNotConfiguredError):
            manager.set_fallback_chain(["ghost"])


class TestReadiness:
    def test_not_ready_without_providers(self):
        assert LLMManager().is_ready() is False

    def test_not_ready_while_key_is_missing(self):
        manager = LLMManager()
        manager.register_provider(_provider("cloud"))

        assert manager.is_ready() is False

    def test_ready_once_player_entered_a_key(self):
        manager = LLMManager()
        manager.register_provider(_provider("cloud"))

        manager.add_api_key("cloud", "sk-player")

        assert manager.is_ready() is True

    def test_local_provider_is_ready_without_keys(self):
        manager = LLMManager()
        manager.register_provider(_provider("local", requires_key=False))

        assert manager.is_ready() is True


class TestGeneration:
    async def test_request_goes_to_the_active_provider(self):
        cloud = ScriptedClient("cloud", answer="Летопись")
        manager = LLMManager(client_factory=ClientRegistry(cloud=cloud))
        manager.register_provider(_provider("cloud", requires_key=False))

        assert await manager.generate_text("system", "user") == "Летопись"
        assert cloud.calls == 1

    async def test_structured_request_is_delegated(self):
        payload = {"declare_war": True, "tribute_gold": 10, "reason": "Провокация"}
        cloud = ScriptedClient("cloud", answer=payload)
        manager = LLMManager(client_factory=ClientRegistry(cloud=cloud))
        manager.register_provider(_provider("cloud", requires_key=False))

        decision = await manager.generate_structured("system", "user", WarCouncilDecision)

        assert decision.declare_war is True
        assert decision.tribute_gold == 10

    async def test_client_is_built_once_and_reused(self):
        cloud = ScriptedClient("cloud", answer="ok")
        registry = ClientRegistry(cloud=cloud)
        manager = LLMManager(client_factory=registry)
        manager.register_provider(_provider("cloud", requires_key=False))

        await manager.generate_text("system", "user")
        await manager.generate_text("system", "user")

        assert registry.built == ["cloud"]
        assert cloud.calls == 2

    async def test_reregistering_provider_rebuilds_client(self):
        cloud = ScriptedClient("cloud", answer="ok")
        registry = ClientRegistry(cloud=cloud)
        manager = LLMManager(client_factory=registry)
        manager.register_provider(_provider("cloud", requires_key=False))
        await manager.generate_text("system", "user")

        manager.register_provider(_provider("cloud", requires_key=False))
        await manager.generate_text("system", "user")

        assert registry.built == ["cloud", "cloud"]

    async def test_request_without_providers_raises(self):
        with pytest.raises(LLMProviderNotConfiguredError):
            await LLMManager().generate_text("system", "user")


class TestFallbackChain:
    async def test_failed_cloud_falls_back_to_local(self):
        """Партия не должна вставать из-за отвалившегося облака."""
        cloud = ScriptedClient("cloud", error=LLMRateLimitError("cloud", "model-cloud", "429"))
        local = ScriptedClient("local", answer="Ответ локальной модели")
        manager = LLMManager(client_factory=ClientRegistry(cloud=cloud, local=local))
        manager.register_provider(_provider("cloud", requires_key=False))
        manager.register_provider(_provider("local", requires_key=False))
        manager.set_fallback_chain(["local"])

        assert await manager.generate_text("system", "user") == "Ответ локальной модели"
        assert cloud.calls == 1
        assert local.calls == 1

    async def test_provider_without_keys_is_skipped(self):
        cloud = ScriptedClient("cloud", answer="облако")
        local = ScriptedClient("local", answer="локально")
        manager = LLMManager(client_factory=ClientRegistry(cloud=cloud, local=local))
        manager.register_provider(_provider("cloud"))  # ключ игрок не ввел
        manager.register_provider(_provider("local", requires_key=False))
        manager.set_fallback_chain(["local"])

        assert await manager.generate_text("system", "user") == "локально"
        assert cloud.calls == 0

    async def test_last_error_surfaces_when_everyone_fails(self):
        cloud = ScriptedClient("cloud", error=LLMRateLimitError("cloud", "model-cloud", "429"))
        local = ScriptedClient("local", error=LLMRequestFailedError("local", "model-local", "сервер не отвечает"))
        manager = LLMManager(client_factory=ClientRegistry(cloud=cloud, local=local))
        manager.register_provider(_provider("cloud", requires_key=False))
        manager.register_provider(_provider("local", requires_key=False))
        manager.set_fallback_chain(["local"])

        with pytest.raises(LLMRequestFailedError) as excinfo:
            await manager.generate_text("system", "user")

        assert excinfo.value.provider_id == "local"

    async def test_missing_keys_everywhere_reports_key_error(self):
        manager = LLMManager(client_factory=ClientRegistry())
        manager.register_provider(_provider("cloud"))

        with pytest.raises(LLMKeyMissingError):
            await manager.generate_text("system", "user")

    async def test_active_provider_is_not_called_twice_in_the_chain(self):
        cloud = ScriptedClient("cloud", answer="ok")
        manager = LLMManager(client_factory=ClientRegistry(cloud=cloud))
        manager.register_provider(_provider("cloud", requires_key=False))
        manager.set_fallback_chain(["cloud"])

        await manager.generate_text("system", "user")

        assert cloud.calls == 1


class TestKeysFacade:
    def test_keys_are_managed_through_the_facade(self):
        keys = ApiKeyManager()
        manager = LLMManager(key_manager=keys)
        manager.register_provider(_provider("cloud"))

        manager.set_api_keys("cloud", ["sk-a", "sk-b"])

        assert len(manager.list_api_keys("cloud")) == 2
        assert keys.has_keys("cloud") is True

    def test_facade_never_returns_raw_secrets(self):
        manager = LLMManager()
        manager.register_provider(_provider("cloud"))
        manager.add_api_key("cloud", "sk-proj-supersecret")

        assert all("supersecret" not in view.masked_value for view in manager.list_api_keys())


class TestProtocolCompliance:
    def test_manager_is_interchangeable_with_a_client(self):
        assert isinstance(LLMManager(), LLMClientProtocol)
