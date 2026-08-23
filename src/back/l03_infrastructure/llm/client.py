"""
Асинхронный клиент-обертка для LLM.

Инкапсулирует пулы HTTP-соединений и обеспечивает бесшовную интеграцию
с любыми OpenAI-совместимыми провайдерами (OpenRouter, локальные сети и т.д.).
"""

import httpx
from openai import AsyncOpenAI
from typing import Optional, Dict

from src.back.utils.logger import main_logger
from src.back.l03_infrastructure.llm.keys.rotator import APIKeyRotator


class LLMClient:
    """
    Управляет HTTP-сессиями для одного провайдера LLM.
    Привязывает каждую сессию к конкретному ключу для оптимизации сетевых запросов.
    """

    def __init__(
        self,
        provider_id: str,
        api_url: Optional[str],
        rotator: APIKeyRotator,
        proxy_url: Optional[str] = None,
    ) -> None:
        self.provider_id = provider_id
        self.api_url = api_url
        self.rotator = rotator
        self.proxy_url = proxy_url

        self._sessions: Dict[str, AsyncOpenAI] = {}
        self._default_session: Optional[AsyncOpenAI] = None

        # Нормализация URL
        if self.api_url and not self.api_url.startswith(("http://", "https://")):
            if "localhost" in self.api_url or "127.0.0.1" in self.api_url:
                self.api_url = f"http://{self.api_url}"
            else:
                self.api_url = f"https://{self.api_url}"

        url_log = self.api_url if self.api_url else "официальный эндпоинт OpenAI"
        main_logger.info(f"[LLM] Клиент '{self.provider_id}' инициализирован ({url_log}).")

    def get_session(self) -> AsyncOpenAI:
        """
        Отдает закэшированную сессию OpenAI с активным "живым" ключом.
        """
        api_key = self.rotator.get_next_key()

        # Если ключей нет, предполагаем, что это локальная модель
        if not api_key:
            if self._default_session is None:
                http_client = (
                    httpx.AsyncClient(proxy=self.proxy_url) if self.proxy_url else None
                )
                self._default_session = AsyncOpenAI(
                    api_key="no-key-required",
                    base_url=self.api_url,
                    http_client=http_client,
                )
            return self._default_session

        # Кэшируем сессии по ключу, чтобы httpx переиспользовал keep-alive соединения
        if api_key not in self._sessions:
            http_client = httpx.AsyncClient(proxy=self.proxy_url) if self.proxy_url else None
            self._sessions[api_key] = AsyncOpenAI(
                api_key=api_key,
                base_url=self.api_url,
                http_client=http_client,
            )

        return self._sessions[api_key]

    async def close(self) -> None:
        """
        Корректно закрывает все активные пулы HTTP-соединений.
        Вызывается при остановке сервера игры.
        """
        for session in self._sessions.values():
            await session.close()
        self._sessions.clear()

        if self._default_session:
            await self._default_session.close()
            self._default_session = None

        main_logger.info(f"[LLM] Все HTTP-сессии клиента '{self.provider_id}' закрыты.")
