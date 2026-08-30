"""
Асинхронный транспортный клиент для работы с OpenAI-совместимыми API.

Инкапсулирует пулы HTTP-соединений, ротацию ключей, сетевые повторы (retries),
обработку Rate Limits (HTTP 429), отсеивание невалидных ключей (HTTP 401) и таймауты.
"""

import asyncio
import time
from typing import Any, Optional

import httpx
import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from src.back.l01_domain.exceptions.llm import (
    LLMAuthorizationError,
    LLMRequestFailedError,
)
from src.back.l03_infrastructure.llm.keys.rotator import (
    AllKeysExhaustedError,
    APIKeyRotator,
)
from src.back.utils.logger import main_logger


class LLMClient:
    """
    Транспортный клиент языковых моделей.
    Управляет HTTP-сессиями и выполняет вызовы API с гарантией обработки сетевых сбоев.
    """

    def __init__(
        self,
        provider_id: str,
        api_url: Optional[str],
        rotator: APIKeyRotator,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        proxy_url: Optional[str] = None,
    ) -> None:
        self.provider_id = provider_id
        self.api_url = api_url
        self.rotator = rotator
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.proxy_url = proxy_url

        self._sessions: dict[str, AsyncOpenAI] = {}
        self._default_session: Optional[AsyncOpenAI] = None

        # Нормализация URL
        if self.api_url and not self.api_url.startswith(("http://", "https://")):
            if "localhost" in self.api_url or "127.0.0.1" in self.api_url:
                self.api_url = f"http://{self.api_url}"
            else:
                self.api_url = f"https://{self.api_url}"

        url_log = self.api_url if self.api_url else "официальный эндпоинт OpenAI"
        main_logger.info(f"[LLM] Клиент '{self.provider_id}' инициализирован ({url_log}).")

    # =========================================================================
    # Сетевой транспорт
    # =========================================================================

    async def create_chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> ChatCompletion:
        """
        Выполняет сетевой запрос к API чат-комплишенов с циклом повторов при сбоях.
        Возвращает сырой ответ модели ChatCompletion.
        """
        timeout_count = 0

        # Формируем аргументы запроса, исключая пустые значения
        api_kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "timeout": self.timeout_seconds,
        }
        api_kwargs.update({k: v for k, v in kwargs.items() if v is not None})

        for attempt in range(self.max_retries + 1):
            session: Optional[AsyncOpenAI] = None

            try:
                session = self.get_session()
                return await session.chat.completions.create(**api_kwargs)

            except AllKeysExhaustedError as err:
                main_logger.warning(
                    f"[LLM] Все ключи провайдера '{self.provider_id}' временно заморожены. "
                    f"Ожидание {err.wait_time} сек..."
                )
                await asyncio.sleep(err.wait_time + 1)
                continue

            except openai.RateLimitError as err:
                wait_time = self._calculate_rate_limit_cooldown(err)
                if session is not None and getattr(session, "api_key", None):
                    self.rotator.cooldown_key(session.api_key, wait_time)

                if self.rotator.total_keys() <= 1:
                    await asyncio.sleep(wait_time + 1)
                else:
                    await asyncio.sleep(1)  # Переключаемся на следующий доступный ключ
                continue

            except openai.AuthenticationError:
                if session is not None and getattr(session, "api_key", None):
                    self.rotator.ban_key(session.api_key)

                if self.rotator.total_keys() == 0:
                    raise LLMAuthorizationError(
                        self.provider_id,
                        model,
                        "все предоставленные API-ключи отклонены провайдером",
                    )
                continue

            except (openai.APITimeoutError, asyncio.TimeoutError) as err:
                timeout_count += 1
                if timeout_count > self.max_retries:
                    raise LLMRequestFailedError(
                        self.provider_id, model, "таймаут ответа провайдера"
                    ) from err

                main_logger.warning(
                    f"[LLM] Таймаут запроса к '{model}' ({timeout_count}/{self.max_retries}). Повтор..."
                )
                continue

            except openai.APIError as err:
                if attempt == self.max_retries:
                    raise LLMRequestFailedError(self.provider_id, model, str(err)) from err

                main_logger.error(
                    f"[LLM] Ошибка API провайдера '{self.provider_id}': {err}. Повтор через 2 сек..."
                )
                await asyncio.sleep(2)
                continue

            except Exception as err:  # Ошибки сети, DNS или сокетов
                raise LLMRequestFailedError(self.provider_id, model, str(err)) from err

        raise LLMRequestFailedError(
            self.provider_id, model, "превышено максимальное число попыток запроса"
        )

    # =========================================================================
    # Управление сессиями
    # =========================================================================

    def get_session(self) -> AsyncOpenAI:
        """
        Отдает закэшированную сессию OpenAI с активным рабочим ключом.
        """
        api_key = self.rotator.get_next_key()

        # Если ключей нет, работаем в режиме локального сервера
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

        # Кэшируем сессии по ключам для переиспользования keep-alive соединений
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
        Закрывает все открытые HTTP-сессии.
        """
        for session in self._sessions.values():
            await session.close()
        self._sessions.clear()

        if self._default_session is not None:
            await self._default_session.close()
            self._default_session = None

        main_logger.info(f"[LLM] Все HTTP-сессии клиента '{self.provider_id}' закрыты.")

    # =========================================================================
    # Вспомогательные методы
    # =========================================================================

    def _calculate_rate_limit_cooldown(self, error: openai.RateLimitError) -> int:
        """
        Определяет длительность заморозки ключа на основе ответа провайдера.
        """
        err_code = getattr(error.body, "get", lambda _: None)("code")
        if err_code == "insufficient_quota" or "billing" in str(error).lower():
            return 86400  # Квота исчерпана — блокируем ключ на 24 часа

        wait_time = 30
        if error.response is not None:
            headers = error.response.headers
            retry_after = headers.get("retry-after") or headers.get("x-ratelimit-reset")
            if retry_after:
                try:
                    parsed = float(retry_after)
                    if parsed > time.time():  # Формат UNIX-timestamp
                        wait_time = int(parsed - time.time())
                    else:
                        wait_time = int(parsed)
                except ValueError:
                    pass

        return max(2, min(wait_time, 300))
