"""
Изолированный исполнитель запросов к LLM.

Инкапсулирует логику общения с OpenAI-совместимыми API:
- Управление ретраями (сетевые ошибки и таймауты).
- Обработка Rate Limits (HTTP 429) и удаление мертвых ключей (HTTP 401).
- Валидация JSON-схем и авто-исправление ответов модели при ошибках Pydantic.
"""

import asyncio
import json
import re
import time
from typing import Any, Optional, Type, TypeVar

import openai
from pydantic import BaseModel, ValidationError

from src.back.utils.logger import main_logger
from src.back.l01_domain.exceptions.llm import (
    LLMAuthorizationError,
    LLMRequestFailedError,
    LLMResponseFormatError,
)
from src.back.l01_domain.llm.models.provider import LLMProviderConfig
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l03_infrastructure.llm.client import LLMClient
from src.back.l03_infrastructure.llm.keys.rotator import AllKeysExhaustedError

T = TypeVar("T", bound=BaseModel)

# Регулярка для очистки ответа от markdown-форматирования (```json ... ```)
_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class LLMExecutor(LLMClientProtocol):
    """
    Единая точка входа для вызова языковых моделей.
    Скрывает всю сложность обработки сети и адаптации ответов.
    """

    def __init__(self, config: LLMProviderConfig, client: LLMClient) -> None:
        self.config = config
        self.client = client

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Генерация свободного текста (письма, летописи, слухи).
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self._execute_network_call(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.6,
    ) -> T:
        """
        Генерация строго валидированного JSON по Pydantic-модели.
        """

        schema = self._harden_schema(response_model.model_json_schema())
        response_format = self._build_response_format(response_model.__name__, schema)

        system_content = system_prompt
        # Если провайдер (например, локальный) не поддерживает строгий json_schema,
        # зашиваем схему текстом в системный промпт
        if not self.config.supports_json_schema:
            system_content = (
                f"{system_prompt}\n\n"
                "Ответь строго одним JSON-объектом по схеме ниже, без пояснений и markdown.\n"
                f"{json.dumps(schema, ensure_ascii=False)}"
            )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ]

        last_error = ""
        # Цикл авто-исправления JSON
        for attempt in range(self.config.structured_retries + 1):
            response = await self._execute_network_call(
                messages=messages,
                temperature=temperature,
                response_format=response_format,
            )
            raw_content = response.choices[0].message.content or ""
            clean_json = self._extract_json(raw_content)

            try:
                return response_model.model_validate_json(clean_json)
            except (ValidationError, ValueError) as e:
                last_error = str(e)
                main_logger.warning(
                    f"[LLM] Модель '{self.config.model}' вернула невалидный JSON "
                    f"(попытка {attempt + 1}): {last_error}"
                )
                # Добавляем ошибку в контекст и заставляем модель исправить её
                messages.append({"role": "assistant", "content": raw_content})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Твой ответ не прошел валидацию схемы. Ошибка:\n{last_error}\nВерни исправленный JSON-объект.",
                    }
                )

        raise LLMResponseFormatError(self.config.model, last_error)

    # =========================================================================
    # Внутренние механизмы сети и парсинга
    # =========================================================================

    async def _execute_network_call(self, **kwargs: Any) -> Any:
        """
        Сетевой цикл с обработкой лимитов, банов ключей и таймаутов.
        """
        timeout_count = 0

        # Подготавливаем аргументы (убираем None)
        api_kwargs = {"model": self.config.model}
        api_kwargs.update({k: v for k, v in kwargs.items() if v is not None})

        for attempt in range(self.config.max_retries + 1):
            try:
                session = self.client.get_session()
                # Вызов SDK OpenAI
                return await session.chat.completions.create(**api_kwargs)

            except AllKeysExhaustedError as e:
                await asyncio.sleep(e.wait_time + 1)
                continue

            except openai.RateLimitError as e:
                wait_time = self._calculate_rate_limit_cooldown(e)
                self.client.rotator.cooldown_key(session.api_key, wait_time)
                if self.client.rotator.total_keys() <= 1:
                    await asyncio.sleep(wait_time + 1)
                else:
                    await asyncio.sleep(1)  # Быстрый переход к следующему ключу
                continue

            except openai.AuthenticationError:
                self.client.rotator.ban_key(session.api_key)
                if self.client.rotator.total_keys() == 0:
                    raise LLMAuthorizationError(
                        self.config.id, self.config.model, "Все ключи забанены."
                    )
                continue

            except (openai.APITimeoutError, asyncio.TimeoutError) as e:
                timeout_count += 1
                if timeout_count > self.config.max_retries:
                    raise LLMRequestFailedError(
                        self.config.id, self.config.model, "Таймаут провайдера."
                    ) from e
                main_logger.warning(
                    f"[LLM] Таймаут ({timeout_count}/{self.config.max_retries}). Повтор..."
                )
                continue

            except openai.APIError as e:
                if attempt == self.config.max_retries:
                    raise LLMRequestFailedError(
                        self.config.id, self.config.model, str(e)
                    ) from e
                main_logger.error(f"[LLM] Ошибка API: {e}. Повтор через 2 сек...")
                await asyncio.sleep(2)
                continue

            except Exception as e:  # Падение DNS или отвал локальной сети
                raise LLMRequestFailedError(self.config.id, self.config.model, str(e)) from e

        raise LLMRequestFailedError(
            self.config.id, self.config.model, "Превышено число попыток."
        )

    def _calculate_rate_limit_cooldown(self, error: openai.RateLimitError) -> int:
        """
        Извлекает время заморозки ключа из заголовков ответа провайдера.
        """

        err_code = getattr(error.body, "get", lambda x: None)("code")
        if err_code == "insufficient_quota" or "billing" in str(error).lower():
            return 86400  # Денег нет, морозим на 24 часа

        wait_time = 30
        if error.response is not None:
            headers = error.response.headers
            retry_after = headers.get("retry-after") or headers.get("x-ratelimit-reset")
            if retry_after:
                try:
                    wait_time = int(float(retry_after))
                    if wait_time > time.time():  # Если вернули UNIX timestamp
                        wait_time = int(wait_time - time.time())
                except ValueError:
                    pass
        return max(2, min(wait_time, 300))

    def _build_response_format(self, name: str, schema: dict) -> dict:
        if not self.config.supports_json_schema:
            return {"type": "json_object"}
        return {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "schema": schema,
                "strict": self.config.strict_json_schema,
            },
        }

    def _harden_schema(self, schema: dict) -> dict:
        """
        Добавляет additionalProperties: false для строгого режима (Strict JSON).
        """
        
        if schema.get("type") == "object":
            schema.setdefault("additionalProperties", False)
        for key in ("properties", "$defs", "definitions"):
            for value in schema.get(key, {}).values():
                if isinstance(value, dict):
                    self._harden_schema(value)
        for key in ("items", "additionalItems"):
            value = schema.get(key)
            if isinstance(value, dict):
                self._harden_schema(value)
        return schema

    def _extract_json(self, raw: str) -> str:
        fenced = _JSON_FENCE.match(raw)
        return fenced.group(1) if fenced else raw.strip()
