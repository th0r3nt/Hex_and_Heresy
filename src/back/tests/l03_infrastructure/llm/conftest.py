"""
Общие фейки и фикстуры для тестов инфраструктуры LLM.

Настоящая сеть здесь не поднимается: вместо OpenAI-сессий подставляются
скриптованные заглушки, а ход времени и `asyncio.sleep` берутся под контроль,
чтобы тесты ретраев и кулдаунов шли мгновенно.
"""

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Union

import openai
import pytest

from src.back.l01_domain.llm.models.provider import LLMProviderConfig
from src.back.l03_infrastructure.llm import executor as executor_module
from src.back.l03_infrastructure.llm.keys import rotator as rotator_module
from src.back.l03_infrastructure.llm.keys.rotator import APIKeyRotator

# Элемент сценария ответов: либо текст ответа модели, либо исключение
Behavior = Union[str, BaseException]


# =========================================================================
# Время
# =========================================================================


class FakeClock:
    """Управляемые часы вместо `time.time()`."""

    def __init__(self, start: float = 1_700_000_000.0) -> None:
        self.now = start

    def time(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    """Подменяет часы внутри ротатора ключей."""
    fake = FakeClock()
    monkeypatch.setattr(rotator_module, "time", SimpleNamespace(time=fake.time))
    return fake


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> List[float]:
    """
    Отключает реальные паузы в исполнителе и записывает их длительности.
    """
    recorded: List[float] = []

    async def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(
        executor_module,
        "asyncio",
        SimpleNamespace(sleep=fake_sleep, TimeoutError=asyncio.TimeoutError),
    )
    return recorded


# =========================================================================
# Ответы и ошибки провайдера
# =========================================================================


def make_completion(content: str) -> Any:
    """Минимальный аналог ChatCompletion из SDK OpenAI."""
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def make_http_response(status_code: int, headers: Optional[Dict[str, str]] = None) -> Any:
    """
    Заглушка httpx-ответа: SDK читает у него только request, status_code и headers.
    """
    return SimpleNamespace(
        request=SimpleNamespace(),
        status_code=status_code,
        headers=dict(headers or {}),
    )


def rate_limit_error(
    message: str = "Rate limit reached",
    headers: Optional[Dict[str, str]] = None,
    body: Any = None,
) -> openai.RateLimitError:
    return openai.RateLimitError(
        message, response=make_http_response(429, headers), body=body
    )


def auth_error(message: str = "Invalid API key") -> openai.AuthenticationError:
    return openai.AuthenticationError(
        message, response=make_http_response(401), body=None
    )


def api_error(message: str = "Internal server error") -> openai.APIError:
    return openai.APIError(message, request=SimpleNamespace(), body=None)


def timeout_error() -> openai.APITimeoutError:
    return openai.APITimeoutError(request=SimpleNamespace())


# =========================================================================
# Фейковые сессия и клиент
# =========================================================================


class FakeSession:
    """Заглушка AsyncOpenAI, привязанная к конкретному ключу."""

    def __init__(self, api_key: str, client: "FakeLLMClient") -> None:
        self.api_key = api_key
        self.closed = False
        self._client = client
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs: Any) -> Any:
        return await self._client.handle_call(self.api_key, kwargs)

    async def close(self) -> None:
        self.closed = True


class FakeLLMClient:
    """
    Заглушка LLMClient: раздает сессии по живым ключам настоящего ротатора
    и отвечает по заранее заданному сценарию.
    """

    def __init__(self, rotator: APIKeyRotator, script: Optional[List[Behavior]] = None) -> None:
        self.rotator = rotator
        self.provider_id = rotator.provider_id
        self.script: List[Behavior] = list(script or [])
        self.calls: List[Dict[str, Any]] = []
        self.used_keys: List[str] = []
        self.closed = False
        self._sessions: Dict[str, FakeSession] = {}

    def get_session(self) -> FakeSession:
        api_key = self.rotator.get_next_key() or "no-key-required"
        if api_key not in self._sessions:
            self._sessions[api_key] = FakeSession(api_key, self)
        return self._sessions[api_key]

    async def handle_call(self, api_key: str, kwargs: Dict[str, Any]) -> Any:
        # Копируем messages: исполнитель дописывает их между попытками
        snapshot = dict(kwargs)
        if "messages" in snapshot:
            snapshot["messages"] = [dict(m) for m in snapshot["messages"]]

        self.calls.append(snapshot)
        self.used_keys.append(api_key)

        assert self.script, "Сценарий ответов исчерпан: модель вызвали лишний раз."
        behavior = self.script.pop(0)

        if isinstance(behavior, BaseException):
            raise behavior
        return make_completion(behavior)

    async def close(self) -> None:
        self.closed = True


# =========================================================================
# Фикстуры
# =========================================================================


def make_config(**overrides: Any) -> LLMProviderConfig:
    """Конфиг провайдера с разумными значениями по умолчанию."""
    data: Dict[str, Any] = {
        "id": "test_provider",
        "title": "Тестовый провайдер",
        "model": "test-model",
    }
    data.update(overrides)
    return LLMProviderConfig(**data)


@pytest.fixture
def config() -> LLMProviderConfig:
    return make_config()


@pytest.fixture
def rotator() -> APIKeyRotator:
    return APIKeyRotator(provider_id="test_provider", keys=["key-alpha", "key-bravo"])


@pytest.fixture
def llm_fakes() -> SimpleNamespace:
    """
    Единая точка доступа к фейкам: тесты не импортируют conftest напрямую,
    поэтому фабрики раздаются через фикстуру.
    """
    return SimpleNamespace(
        completion=make_completion,
        http_response=make_http_response,
        rate_limit_error=rate_limit_error,
        auth_error=auth_error,
        api_error=api_error,
        timeout_error=timeout_error,
        Client=FakeLLMClient,
        Session=FakeSession,
        Rotator=APIKeyRotator,
        config=make_config,
    )
