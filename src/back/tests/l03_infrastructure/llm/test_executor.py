"""
Тесты исполнителя запросов к LLM: сетевой цикл (лимиты, баны, таймауты),
подготовка JSON-схем и авто-исправление невалидных ответов модели.
"""

import json
import time
from typing import List, Optional

import pytest
from pydantic import BaseModel

from src.back.l01_domain.exceptions import (
    LLMAuthorizationError,
    LLMRequestFailedError,
    LLMResponseFormatError,
)
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l03_infrastructure.llm.executor import LLMExecutor
from src.back.l03_infrastructure.llm.keys.rotator import (
    AllKeysExhaustedError,
    APIKeyRotator,
)


class BattlePlan(BaseModel):
    """Схема структурированного ответа для тестов."""

    decision: str
    confidence: int


class Squad(BaseModel):
    name: str


class Deployment(BaseModel):
    """Вложенная схема: проверяем рекурсивное ужесточение."""

    squads: List[Squad]
    reserve: Optional[Squad] = None


@pytest.fixture
def build(llm_fakes):
    """Собирает исполнителя с фейковым клиентом по сценарию ответов."""

    def _build(script, keys=("key-alpha",), **config_overrides):
        rotator = APIKeyRotator(provider_id="test_provider", keys=list(keys))
        client = llm_fakes.Client(rotator, list(script))
        executor = LLMExecutor(config=llm_fakes.config(**config_overrides), client=client)
        return executor, client

    return _build


class TestContract:
    def test_executor_implements_llm_client_protocol(self, build):
        executor, _ = build([])

        assert isinstance(executor, LLMClientProtocol)


class TestGenerateText:
    async def test_returns_model_content(self, build):
        executor, client = build(["Лорд склоняет голову."])

        result = await executor.generate_text(
            system_prompt="Ты — лорд.", user_prompt="Ответь на письмо."
        )

        assert result == "Лорд склоняет голову."
        assert client.calls[0]["model"] == "test-model"
        assert client.calls[0]["messages"] == [
            {"role": "system", "content": "Ты — лорд."},
            {"role": "user", "content": "Ответь на письмо."},
        ]

    async def test_empty_content_becomes_empty_string(self, build):
        executor, client = build([""])

        assert await executor.generate_text(system_prompt="s", user_prompt="u") == ""

    async def test_none_arguments_are_not_sent_to_provider(self, build):
        executor, client = build(["ок"])

        await executor.generate_text(
            system_prompt="s", user_prompt="u", temperature=0.3, max_tokens=None
        )

        assert client.calls[0]["temperature"] == 0.3
        assert "max_tokens" not in client.calls[0]

    async def test_max_tokens_is_forwarded(self, build):
        executor, client = build(["ок"])

        await executor.generate_text(system_prompt="s", user_prompt="u", max_tokens=256)

        assert client.calls[0]["max_tokens"] == 256


class TestGenerateStructured:
    async def test_valid_json_is_parsed_into_model(self, build):
        executor, client = build(['{"decision": "атаковать", "confidence": 3}'])

        plan = await executor.generate_structured(
            system_prompt="s", user_prompt="u", response_model=BattlePlan
        )

        assert isinstance(plan, BattlePlan)
        assert plan.decision == "атаковать"
        assert plan.confidence == 3

    async def test_markdown_fence_is_stripped(self, build):
        fenced = '```json\n{"decision": "отступить", "confidence": 1}\n```'
        executor, _ = build([fenced])

        plan = await executor.generate_structured(
            system_prompt="s", user_prompt="u", response_model=BattlePlan
        )

        assert plan.decision == "отступить"

    async def test_json_schema_is_sent_when_provider_supports_it(self, build):
        executor, client = build(['{"decision": "d", "confidence": 1}'])

        await executor.generate_structured(
            system_prompt="s", user_prompt="u", response_model=BattlePlan
        )

        response_format = client.calls[0]["response_format"]
        assert response_format["type"] == "json_schema"
        assert response_format["json_schema"]["name"] == "BattlePlan"
        assert response_format["json_schema"]["strict"] is False
        assert response_format["json_schema"]["schema"]["additionalProperties"] is False

    async def test_strict_mode_is_taken_from_config(self, build):
        executor, client = build(
            ['{"decision": "d", "confidence": 1}'], strict_json_schema=True
        )

        await executor.generate_structured(
            system_prompt="s", user_prompt="u", response_model=BattlePlan
        )

        assert client.calls[0]["response_format"]["json_schema"]["strict"] is True

    async def test_schema_goes_into_prompt_for_weak_providers(self, build):
        executor, client = build(
            ['{"decision": "d", "confidence": 1}'], supports_json_schema=False
        )

        await executor.generate_structured(
            system_prompt="Ты — лорд.", user_prompt="u", response_model=BattlePlan
        )

        call = client.calls[0]
        assert call["response_format"] == {"type": "json_object"}
        system_content = call["messages"][0]["content"]
        assert system_content.startswith("Ты — лорд.")
        assert "confidence" in system_content  # схема зашита текстом

    async def test_invalid_json_triggers_self_correction(self, build):
        executor, client = build(
            ['{"decision": "атака"}', '{"decision": "атака", "confidence": 2}']
        )

        plan = await executor.generate_structured(
            system_prompt="s", user_prompt="u", response_model=BattlePlan
        )

        assert plan.confidence == 2
        assert len(client.calls) == 2

        # Во второй запрос уехали ответ модели и текст ошибки валидации
        repair_messages = client.calls[1]["messages"]
        assert len(repair_messages) == 4
        assert repair_messages[2]["role"] == "assistant"
        assert repair_messages[3]["role"] == "user"
        assert "не прошел валидацию" in repair_messages[3]["content"]

    async def test_retries_are_limited_by_config(self, build):
        executor, client = build(["не json", "тоже не json"], structured_retries=1)

        with pytest.raises(LLMResponseFormatError) as exc_info:
            await executor.generate_structured(
                system_prompt="s", user_prompt="u", response_model=BattlePlan
            )

        assert len(client.calls) == 2
        assert exc_info.value.model == "test-model"

    async def test_single_attempt_when_retries_disabled(self, build):
        executor, client = build(["не json"], structured_retries=0)

        with pytest.raises(LLMResponseFormatError):
            await executor.generate_structured(
                system_prompt="s", user_prompt="u", response_model=BattlePlan
            )

        assert len(client.calls) == 1


class TestSchemaHardening:
    def test_nested_schemas_forbid_extra_fields(self, build):
        executor, _ = build([])

        schema = executor._harden_schema(Deployment.model_json_schema())

        assert schema["additionalProperties"] is False
        assert schema["$defs"]["Squad"]["additionalProperties"] is False

    def test_hardening_is_idempotent(self, build):
        executor, _ = build([])

        once = executor._harden_schema(BattlePlan.model_json_schema())
        twice = executor._harden_schema(json.loads(json.dumps(once)))

        assert once == twice


class TestJsonExtraction:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ('{"a": 1}', '{"a": 1}'),
            ('   {"a": 1}   ', '{"a": 1}'),
            ('```json\n{"a": 1}\n```', '{"a": 1}'),
            ('```\n{"a": 1}\n```', '{"a": 1}'),
        ],
    )
    def test_fences_and_spaces_are_removed(self, build, raw: str, expected: str):
        executor, _ = build([])

        assert executor._extract_json(raw) == expected


class TestNetworkResilience:
    async def test_rate_limit_freezes_key_and_switches_to_next(
        self, build, llm_fakes, sleeps
    ):
        executor, client = build(
            [llm_fakes.rate_limit_error(headers={"retry-after": "45"}), "готово"],
            keys=("key-alpha", "key-bravo"),
        )

        result = await executor.generate_text(system_prompt="s", user_prompt="u")

        assert result == "готово"
        assert client.used_keys == ["key-alpha", "key-bravo"]
        assert sleeps == [1]  # есть живой ключ — ждать долго незачем

    async def test_last_key_rate_limit_waits_out_the_cooldown(
        self, build, llm_fakes, sleeps, monkeypatch
    ):
        executor, client = build(
            [llm_fakes.rate_limit_error(headers={"retry-after": "20"}), "готово"],
            keys=("key-alpha",),
        )
        # Единственный ключ заморожен, поэтому вторую попытку пускаем после разморозки
        monkeypatch.setattr(client.rotator, "get_next_key", lambda: "key-alpha")

        result = await executor.generate_text(system_prompt="s", user_prompt="u")

        assert result == "готово"
        assert sleeps == [21]

    async def test_dead_key_is_banned_and_request_survives(self, build, llm_fakes, sleeps):
        executor, client = build(
            [llm_fakes.auth_error(), "готово"], keys=("key-alpha", "key-bravo")
        )

        result = await executor.generate_text(system_prompt="s", user_prompt="u")

        assert result == "готово"
        assert client.rotator.keys == ["key-bravo"]

    async def test_all_keys_banned_raises_authorization_error(
        self, build, llm_fakes, sleeps
    ):
        executor, client = build([llm_fakes.auth_error()], keys=("key-alpha",))

        with pytest.raises(LLMAuthorizationError) as exc_info:
            await executor.generate_text(system_prompt="s", user_prompt="u")

        assert client.rotator.total_keys() == 0
        assert exc_info.value.provider_id == "test_provider"

    async def test_timeouts_are_retried_then_give_up(self, build, llm_fakes, sleeps):
        errors = [llm_fakes.timeout_error() for _ in range(3)]
        executor, client = build(errors, max_retries=2)

        with pytest.raises(LLMRequestFailedError) as exc_info:
            await executor.generate_text(system_prompt="s", user_prompt="u")

        assert len(client.calls) == 3
        assert "Таймаут" in exc_info.value.reason

    async def test_timeout_followed_by_success(self, build, llm_fakes, sleeps):
        executor, _ = build([llm_fakes.timeout_error(), "готово"], max_retries=2)

        assert await executor.generate_text(system_prompt="s", user_prompt="u") == "готово"

    async def test_api_error_is_retried_with_pause(self, build, llm_fakes, sleeps):
        executor, client = build([llm_fakes.api_error(), "готово"], max_retries=2)

        result = await executor.generate_text(system_prompt="s", user_prompt="u")

        assert result == "готово"
        assert sleeps == [2]

    async def test_api_error_on_last_attempt_fails_request(self, build, llm_fakes, sleeps):
        errors = [llm_fakes.api_error("500 Internal") for _ in range(2)]
        executor, client = build(errors, max_retries=1)

        with pytest.raises(LLMRequestFailedError) as exc_info:
            await executor.generate_text(system_prompt="s", user_prompt="u")

        assert len(client.calls) == 2
        assert "500 Internal" in exc_info.value.reason

    async def test_unexpected_error_is_wrapped_immediately(self, build, sleeps):
        executor, client = build([RuntimeError("DNS отвалился")], max_retries=2)

        with pytest.raises(LLMRequestFailedError) as exc_info:
            await executor.generate_text(system_prompt="s", user_prompt="u")

        assert len(client.calls) == 1  # без ретраев: сеть лежит
        assert "DNS отвалился" in exc_info.value.reason

    async def test_exhausted_keys_are_waited_out(self, build, sleeps, monkeypatch):
        executor, client = build(["готово"])
        original = client.get_session
        raised = {"done": False}

        def flaky_session():
            if not raised["done"]:
                raised["done"] = True
                raise AllKeysExhaustedError(wait_time=7)
            return original()

        monkeypatch.setattr(client, "get_session", flaky_session)

        assert await executor.generate_text(system_prompt="s", user_prompt="u") == "готово"
        assert sleeps == [8]

    async def test_permanently_exhausted_keys_end_with_failure(
        self, build, sleeps, monkeypatch
    ):
        executor, client = build([], max_retries=1)

        def always_exhausted():
            raise AllKeysExhaustedError(wait_time=5)

        monkeypatch.setattr(client, "get_session", always_exhausted)

        with pytest.raises(LLMRequestFailedError) as exc_info:
            await executor.generate_text(system_prompt="s", user_prompt="u")

        assert "Превышено число попыток" in exc_info.value.reason
        assert sleeps == [6, 6]


class TestRateLimitCooldown:
    def test_quota_exhaustion_freezes_key_for_a_day(self, build, llm_fakes):
        executor, _ = build([])
        error = llm_fakes.rate_limit_error(body={"code": "insufficient_quota"})

        assert executor._calculate_rate_limit_cooldown(error) == 86400

    def test_billing_message_freezes_key_for_a_day(self, build, llm_fakes):
        executor, _ = build([])
        error = llm_fakes.rate_limit_error("Your billing plan is out of credits")

        assert executor._calculate_rate_limit_cooldown(error) == 86400

    def test_retry_after_header_is_respected(self, build, llm_fakes):
        executor, _ = build([])
        error = llm_fakes.rate_limit_error(headers={"retry-after": "45"})

        assert executor._calculate_rate_limit_cooldown(error) == 45

    def test_reset_header_is_used_as_fallback(self, build, llm_fakes):
        executor, _ = build([])
        error = llm_fakes.rate_limit_error(headers={"x-ratelimit-reset": "12"})

        assert executor._calculate_rate_limit_cooldown(error) == 12

    def test_unix_timestamp_is_converted_to_delay(self, build, llm_fakes):
        executor, _ = build([])
        error = llm_fakes.rate_limit_error(
            headers={"retry-after": str(int(time.time()) + 120)}
        )

        assert 110 <= executor._calculate_rate_limit_cooldown(error) <= 130

    def test_garbage_header_falls_back_to_default(self, build, llm_fakes):
        executor, _ = build([])
        error = llm_fakes.rate_limit_error(headers={"retry-after": "скоро"})

        assert executor._calculate_rate_limit_cooldown(error) == 30

    def test_missing_headers_fall_back_to_default(self, build, llm_fakes):
        executor, _ = build([])

        assert executor._calculate_rate_limit_cooldown(llm_fakes.rate_limit_error()) == 30

    @pytest.mark.parametrize("raw, expected", [("0", 2), ("1", 2), ("99999", 300)])
    def test_cooldown_is_clamped(self, build, llm_fakes, raw: str, expected: int):
        executor, _ = build([])
        error = llm_fakes.rate_limit_error(headers={"retry-after": raw})

        assert executor._calculate_rate_limit_cooldown(error) == expected
