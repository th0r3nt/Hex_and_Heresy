"""
Тест адаптера поверх пакета `openai`: без сети, но с настоящим SDK.
"""

import pytest

from src.back.l01_domain.exceptions import LLMRequestFailedError
from src.back.l01_domain.llm.constants import ChatRole
from src.back.l01_domain.llm.models.chat import ChatMessage
from src.back.l01_domain.llm.models.provider import LLMProviderConfig
from src.back.l03_infrastructure.llm.client import OpenAISDKSessionFactory


@pytest.fixture
def dead_endpoint() -> LLMProviderConfig:
    """Локальный сервер, которого заведомо нет: соединение отвергается сразу."""
    return LLMProviderConfig(
        id="local",
        title="Выключенная локальная модель",
        model="test-model",
        base_url="http://127.0.0.1:1/v1",
        requires_api_key=False,
        timeout_seconds=2.0,
        max_retries=0,
    )


class TestOpenAISDKSessionFactory:
    async def test_unreachable_provider_becomes_domain_error(self, dead_endpoint):
        """Ошибки SDK не должны утекать наружу: выше по стеку про openai не знают."""
        factory = OpenAISDKSessionFactory()

        with pytest.raises(LLMRequestFailedError) as excinfo:
            async with factory.open_session(dead_endpoint, api_key=None) as session:
                await session.complete(
                    messages=[ChatMessage(role=ChatRole.USER, content="привет")],
                    temperature=0.5,
                )

        assert excinfo.value.provider_id == "local"
        assert excinfo.value.model == "test-model"
