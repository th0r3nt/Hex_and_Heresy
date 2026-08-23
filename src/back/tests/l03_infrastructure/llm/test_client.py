"""
Тесты клиента-обертки: нормализация адреса эндпоинта, кэш сессий по ключам
и корректное закрытие пулов соединений.
"""

import pytest
from openai import AsyncOpenAI

from src.back.l03_infrastructure.llm.client import LLMClient
from src.back.l03_infrastructure.llm.keys.rotator import (
    AllKeysExhaustedError,
    APIKeyRotator,
)


def make_client(keys=None, api_url=None, proxy_url=None) -> LLMClient:
    rotator = APIKeyRotator(provider_id="test_provider", keys=list(keys or []))
    return LLMClient(
        provider_id="test_provider",
        api_url=api_url,
        rotator=rotator,
        proxy_url=proxy_url,
    )


class TestUrlNormalization:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("localhost:1234/v1", "http://localhost:1234/v1"),
            ("127.0.0.1:8080/v1", "http://127.0.0.1:8080/v1"),
            ("openrouter.ai/api/v1", "https://openrouter.ai/api/v1"),
            ("https://openrouter.ai/api/v1", "https://openrouter.ai/api/v1"),
            ("http://localhost:1234/v1", "http://localhost:1234/v1"),
        ],
    )
    def test_scheme_is_added_by_host_kind(self, raw: str, expected: str):
        client = make_client(api_url=raw)

        assert client.api_url == expected

    def test_none_url_means_official_openai_endpoint(self):
        client = make_client(api_url=None)

        assert client.api_url is None
        assert str(client.get_session().base_url).startswith("https://api.openai.com")


class TestSessions:
    def test_session_without_keys_is_shared_and_keyless(self):
        client = make_client(keys=[], api_url="localhost:1234/v1")

        first = client.get_session()
        second = client.get_session()

        assert isinstance(first, AsyncOpenAI)
        assert first is second  # локальной модели хватает одной сессии
        assert first.api_key == "no-key-required"
        assert str(first.base_url).startswith("http://localhost:1234")

    def test_each_key_gets_its_own_cached_session(self):
        client = make_client(keys=["alpha", "bravo"])

        first = client.get_session()
        second = client.get_session()
        third = client.get_session()  # круг замкнулся, снова alpha

        assert first.api_key == "alpha"
        assert second.api_key == "bravo"
        assert third is first  # сессия переиспользуется ради keep-alive
        assert len(client._sessions) == 2

    def test_banned_key_is_not_reused(self):
        client = make_client(keys=["alpha", "bravo"])
        client.rotator.ban_key("alpha")

        assert {client.get_session().api_key for _ in range(4)} == {"bravo"}

    def test_exhausted_keys_propagate_to_caller(self):
        client = make_client(keys=["alpha"])
        client.rotator.cooldown_key("alpha", seconds=60)

        with pytest.raises(AllKeysExhaustedError):
            client.get_session()

    def test_proxy_url_does_not_break_session_creation(self):
        client = make_client(keys=["alpha"], proxy_url="http://127.0.0.1:8888")

        session = client.get_session()

        assert isinstance(session, AsyncOpenAI)
        assert session.api_key == "alpha"


class TestClosing:
    async def test_close_releases_all_sessions(self):
        client = make_client(keys=["alpha", "bravo"])
        first = client.get_session()
        second = client.get_session()

        await client.close()

        assert first.is_closed()
        assert second.is_closed()
        assert client._sessions == {}

    async def test_close_releases_default_session(self):
        client = make_client(keys=[], api_url="localhost:1234/v1")
        session = client.get_session()

        await client.close()

        assert session.is_closed()
        assert client._default_session is None

    async def test_close_is_safe_without_any_session(self):
        client = make_client(keys=["alpha"])

        await client.close()  # не должно падать

        assert client._sessions == {}

    async def test_client_is_usable_again_after_close(self):
        client = make_client(keys=["alpha"])
        first = client.get_session()
        await client.close()

        second = client.get_session()

        assert second is not first
        assert not second.is_closed()
