"""
Общие дублеры для тестов инфраструктуры LLM: сессия без сети и провайдеры.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional, Union

import pytest
from pydantic import BaseModel, Field

from src.back.l03_infrastructure.llm.client import (
    ChatMessage,
    ChatSessionProtocol,
    LLMProviderConfig,
)


class FakeSession(ChatSessionProtocol):
    """
    Сессия, отвечающая заранее заготовленным сценарием.
    Элемент сценария - либо текст ответа, либо исключение, которое надо бросить.
    """

    def __init__(self, script: list[Union[str, Exception]], journal: "FakeSessionFactory") -> None:
        self._script = script
        self._journal = journal

    async def complete(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict[str, Any]] = None,
    ) -> str:
        self._journal.requests.append(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": response_format,
            }
        )

        step = self._script.pop(0) if self._script else ""
        if isinstance(step, Exception):
            raise step
        return step


class FakeSessionFactory:
    """
    Фабрика сессий без сети. Ведет журнал открытий, закрытий и запросов.
    """

    def __init__(self, script: Optional[list[Union[str, Exception]]] = None) -> None:
        self.script: list[Union[str, Exception]] = list(script or [])
        self.requests: list[dict[str, Any]] = []
        self.opened_with_keys: list[Optional[str]] = []
        self.closed_sessions = 0

    @asynccontextmanager
    async def open_session(
        self, config: LLMProviderConfig, api_key: Optional[str]
    ) -> AsyncIterator[ChatSessionProtocol]:
        self.opened_with_keys.append(api_key)
        try:
            yield FakeSession(self.script, self)
        finally:
            self.closed_sessions += 1

    @property
    def last_request(self) -> dict[str, Any]:
        return self.requests[-1]


class WarCouncilDecision(BaseModel):
    """Пример структурного ответа: решение ИИ-лорда на переговорах."""

    declare_war: bool
    tribute_gold: int = Field(default=0, ge=0)
    reason: str


@pytest.fixture
def cloud_provider() -> LLMProviderConfig:
    return LLMProviderConfig(
        id="openrouter",
        title="OpenRouter",
        model="test-cloud-model",
        base_url="https://openrouter.ai/api/v1",
    )


@pytest.fixture
def local_provider() -> LLMProviderConfig:
    return LLMProviderConfig(
        id="local",
        title="Локальная модель",
        model="test-local-model",
        base_url="http://localhost:1234/v1",
        requires_api_key=False,
        supports_json_schema=False,
    )
