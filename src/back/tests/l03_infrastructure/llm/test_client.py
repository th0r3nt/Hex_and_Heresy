"""
Тесты OpenAI-совместимого клиента: сессии, структурные ответы и здоровье ключей.
"""

import json

import pytest

from src.back.l01_domain.exceptions import (
    LLMAuthorizationError,
    LLMKeyMissingError,
    LLMRateLimitError,
    LLMResponseFormatError,
)
from src.back.l01_domain.llm.constants import ApiKeyStatus, ChatRole
from src.back.l01_domain.llm.models.provider import LLMProviderConfig
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l03_infrastructure.llm.client import OpenAICompatibleClient
from src.back.l03_infrastructure.llm.keys.manager import ApiKeyManager
from src.back.tests.l03_infrastructure.llm.conftest import (
    FakeSessionFactory,
    WarCouncilDecision,
)


def _keys(provider_id: str = "openrouter", *values: str) -> ApiKeyManager:
    manager = ApiKeyManager()
    manager.set_keys(provider_id, list(values) or ["sk-test"])
    return manager


class TestFreeTextGeneration:
    async def test_prompts_become_system_and_user_messages(self, cloud_provider):
        sessions = FakeSessionFactory(["Орки идут на юг."])
        client = OpenAICompatibleClient(cloud_provider, _keys(), sessions)

        answer = await client.generate_text(
            system_prompt="Ты - летописец.", user_prompt="Опиши битву.", temperature=0.9
        )

        assert answer == "Орки идут на юг."
        messages = sessions.last_request["messages"]
        assert [m.role for m in messages] == [ChatRole.SYSTEM, ChatRole.USER]
        assert messages[0].content == "Ты - летописец."
        assert sessions.last_request["temperature"] == 0.9

    async def test_session_is_closed_after_request(self, cloud_provider):
        sessions = FakeSessionFactory(["ответ"])
        client = OpenAICompatibleClient(cloud_provider, _keys(), sessions)

        await client.generate_text("system", "user")

        assert sessions.closed_sessions == 1

    async def test_session_is_closed_even_when_provider_fails(self, cloud_provider):
        sessions = FakeSessionFactory(
            [LLMRateLimitError("openrouter", "test-cloud-model", "квота")]
        )
        client = OpenAICompatibleClient(cloud_provider, _keys(), sessions)

        with pytest.raises(LLMRateLimitError):
            await client.generate_text("system", "user")

        assert sessions.closed_sessions == 1


class TestStructuredGeneration:
    async def test_valid_json_becomes_pydantic_model(self, cloud_provider):
        payload = {"declare_war": True, "tribute_gold": 0, "reason": "Оскорбление посла"}
        sessions = FakeSessionFactory([json.dumps(payload)])
        client = OpenAICompatibleClient(cloud_provider, _keys(), sessions)

        decision = await client.generate_structured(
            "Ты - лорд.", "Ответь на ультиматум.", WarCouncilDecision
        )

        assert isinstance(decision, WarCouncilDecision)
        assert decision.declare_war is True
        assert decision.reason == "Оскорбление посла"

    async def test_markdown_fence_is_stripped(self, cloud_provider):
        """Модели упорно заворачивают JSON в ```json, даже когда их просят не делать этого."""
        body = json.dumps({"declare_war": False, "tribute_gold": 50, "reason": "Мир выгоднее"})
        sessions = FakeSessionFactory([f"```json\n{body}\n```"])
        client = OpenAICompatibleClient(cloud_provider, _keys(), sessions)

        decision = await client.generate_structured("system", "user", WarCouncilDecision)

        assert decision.tribute_gold == 50

    async def test_invalid_json_triggers_corrective_retry(self, cloud_provider):
        good = json.dumps({"declare_war": False, "tribute_gold": 0, "reason": "Передумал"})
        sessions = FakeSessionFactory(["не JSON, а болтовня", good])
        client = OpenAICompatibleClient(cloud_provider, _keys(), sessions)

        decision = await client.generate_structured("system", "user", WarCouncilDecision)

        assert decision.reason == "Передумал"
        assert len(sessions.requests) == 2

        # Во второй заход модель получает свой прошлый ответ и текст ошибки
        retry_messages = sessions.requests[1]["messages"]
        assert retry_messages[-2].role is ChatRole.ASSISTANT
        assert retry_messages[-2].content == "не JSON, а болтовня"
        assert "не прошел валидацию" in retry_messages[-1].content

    async def test_hopeless_model_raises_format_error(self, cloud_provider):
        sessions = FakeSessionFactory(["мусор", "снова мусор"])
        client = OpenAICompatibleClient(cloud_provider, _keys(), sessions)

        with pytest.raises(LLMResponseFormatError):
            await client.generate_structured("system", "user", WarCouncilDecision)

        assert len(sessions.requests) == 2  # исходный запрос плюс один переспрос

    async def test_retries_can_be_disabled(self, cloud_provider):
        config = cloud_provider.model_copy(update={"structured_retries": 0})
        sessions = FakeSessionFactory(["мусор"])
        client = OpenAICompatibleClient(config, _keys(), sessions)

        with pytest.raises(LLMResponseFormatError):
            await client.generate_structured("system", "user", WarCouncilDecision)

        assert len(sessions.requests) == 1

    async def test_schema_is_sent_machine_readable_when_supported(self, cloud_provider):
        payload = json.dumps({"declare_war": False, "tribute_gold": 0, "reason": "ok"})
        sessions = FakeSessionFactory([payload])
        client = OpenAICompatibleClient(cloud_provider, _keys(), sessions)

        await client.generate_structured("Ты - лорд.", "user", WarCouncilDecision)

        response_format = sessions.last_request["response_format"]
        assert response_format["type"] == "json_schema"
        assert response_format["json_schema"]["name"] == "WarCouncilDecision"
        # Строгий режим провайдеров требует явного запрета лишних полей
        assert response_format["json_schema"]["schema"]["additionalProperties"] is False
        assert "schema" not in sessions.last_request["messages"][0].content

    async def test_schema_falls_back_into_the_prompt_for_simple_servers(self, local_provider):
        payload = json.dumps({"declare_war": False, "tribute_gold": 0, "reason": "ok"})
        sessions = FakeSessionFactory([payload])
        client = OpenAICompatibleClient(local_provider, key_manager=None, session_factory=sessions)

        await client.generate_structured("Ты - лорд.", "user", WarCouncilDecision)

        assert sessions.last_request["response_format"] == {"type": "json_object"}
        system_content = sessions.last_request["messages"][0].content
        assert "declare_war" in system_content


class TestKeyLifecycle:
    async def test_key_is_taken_from_the_pool(self, cloud_provider):
        sessions = FakeSessionFactory(["ответ"])
        client = OpenAICompatibleClient(cloud_provider, _keys("openrouter", "sk-alpha"), sessions)

        await client.generate_text("system", "user")

        assert sessions.opened_with_keys == ["sk-alpha"]

    async def test_local_provider_needs_no_key(self, local_provider):
        sessions = FakeSessionFactory(["ответ"])
        client = OpenAICompatibleClient(local_provider, key_manager=None, session_factory=sessions)

        await client.generate_text("system", "user")

        assert sessions.opened_with_keys == [None]

    async def test_request_without_keys_fails_fast(self, cloud_provider):
        sessions = FakeSessionFactory(["ответ"])
        client = OpenAICompatibleClient(cloud_provider, ApiKeyManager(), sessions)

        with pytest.raises(LLMKeyMissingError):
            await client.generate_text("system", "user")

        assert sessions.requests == []

    async def test_rejected_key_is_disabled(self, cloud_provider):
        keys = _keys("openrouter", "sk-bad")
        sessions = FakeSessionFactory(
            [LLMAuthorizationError("openrouter", "test-cloud-model", "401")]
        )
        client = OpenAICompatibleClient(cloud_provider, keys, sessions)

        with pytest.raises(LLMAuthorizationError):
            await client.generate_text("system", "user")

        assert keys.list_keys("openrouter")[0].status is ApiKeyStatus.REVOKED

    async def test_rate_limited_key_goes_to_cooldown(self, cloud_provider):
        keys = _keys("openrouter", "sk-tired")
        sessions = FakeSessionFactory(
            [LLMRateLimitError("openrouter", "test-cloud-model", "429")]
        )
        client = OpenAICompatibleClient(cloud_provider, keys, sessions)

        with pytest.raises(LLMRateLimitError):
            await client.generate_text("system", "user")

        assert keys.list_keys("openrouter")[0].status is ApiKeyStatus.COOLING_DOWN

    async def test_success_keeps_key_healthy(self, cloud_provider):
        keys = _keys("openrouter", "sk-fine")
        sessions = FakeSessionFactory(["ответ"])
        client = OpenAICompatibleClient(cloud_provider, keys, sessions)

        await client.generate_text("system", "user")

        assert keys.list_keys("openrouter")[0].status is ApiKeyStatus.ACTIVE


class TestProtocolCompliance:
    def test_client_satisfies_domain_protocol(self, cloud_provider):
        client = OpenAICompatibleClient(cloud_provider, ApiKeyManager(), FakeSessionFactory())

        assert isinstance(client, LLMClientProtocol)

    def test_provider_config_is_immutable(self):
        config = LLMProviderConfig(id="p", title="P", model="m")

        with pytest.raises(Exception):
            config.model = "другая"  # type: ignore[misc]
