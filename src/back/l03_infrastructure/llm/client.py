"""
Клиент для запросов к LLM.
Принимает готовый промпт+контекст и возвращает ответ от LLM.

Общение идет по протоколу OpenAI Chat Completions - его понимают и облачные
провайдеры (OpenAI, OpenRouter, DeepSeek, Groq), и локальные серверы
(llama.cpp, LM Studio, Ollama, vLLM). Провайдер отличается только base_url,
именем модели и наличием ключа, поэтому клиент один на всех.
"""

import json
import re
from contextlib import asynccontextmanager
from enum import Enum
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterator,
    Optional,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.back.l01_domain.exceptions import (
    LLMAuthorizationError,
    LLMRateLimitError,
    LLMRequestFailedError,
    LLMResponseFormatError,
)
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l03_infrastructure.llm.keys.manager import ApiKeyManager
from src.back.utils.logger import main_logger

T = TypeVar("T", bound=BaseModel)

# Модели любят оборачивать JSON в markdown-заборчик, даже когда их просят не делать этого
_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class ChatRole(str, Enum):
    """Роли участников диалога в формате Chat Completions."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """Одно сообщение диалога."""

    model_config = ConfigDict(frozen=True)

    role: ChatRole
    content: str

    def to_payload(self) -> dict[str, str]:
        return {"role": self.role.value, "content": self.content}


class LLMProviderConfig(BaseModel):
    """
    Описание одного провайдера: куда стучаться, какой моделью и на каких условиях.
    Игрок задает это в настройках, поэтому конфиг - данные, а не код.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ..., min_length=1, description="Идентификатор провайдера (напр. 'openrouter')"
    )
    title: str = Field(..., min_length=1, description="Название для экрана настроек")
    model: str = Field(..., min_length=1, description="Имя модели у провайдера")

    base_url: Optional[str] = Field(
        default=None,
        description="Адрес OpenAI-совместимого эндпоинта; None - облако OpenAI",
    )
    requires_api_key: bool = Field(
        default=True, description="Локальные серверы обычно работают без ключа"
    )

    timeout_seconds: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=2, ge=0, description="Ретраи транспорта внутри SDK")

    supports_json_schema: bool = Field(
        default=True,
        description=(
            "Понимает ли провайдер response_format=json_schema. Если нет, схема "
            "уезжает текстом в системный промпт, а ответ просто просят в JSON"
        ),
    )
    strict_json_schema: bool = Field(
        default=False,
        description="Строгий режим схемы: поддерживают не все совместимые провайдеры",
    )
    structured_retries: int = Field(
        default=1,
        ge=0,
        description="Сколько раз переспросить модель, если она вернула невалидный JSON",
    )


# ==================================================================
# СЕССИЯ ЗАПРОСА
# ==================================================================


@runtime_checkable
class ChatSessionProtocol(Protocol):
    """
    Контракт открытой сессии: умеет выполнить один запрос к модели.
    """

    async def complete(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict[str, Any]] = None,
    ) -> str: ...


@runtime_checkable
class LLMSessionFactoryProtocol(Protocol):
    """
    Контракт фабрики сессий. Отделяет клиента от конкретного SDK: в тестах
    сюда подставляется фейк, а завтра - другой транспорт.
    """

    def open_session(
        self, config: LLMProviderConfig, api_key: Optional[str]
    ) -> AsyncContextManager[ChatSessionProtocol]: ...


class _OpenAISDKSession(ChatSessionProtocol):
    """
    Сессия поверх официального SDK. Переводит ошибки SDK в доменные исключения,
    чтобы выше по стеку никто не знал про openai.
    """

    def __init__(self, sdk_client: Any, config: LLMProviderConfig, errors: Any) -> None:
        self._client = sdk_client
        self._config = config
        self._errors = errors

    async def complete(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict[str, Any]] = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": [message.to_payload() for message in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format is not None:
            payload["response_format"] = response_format

        try:
            response = await self._client.chat.completions.create(**payload)
        except self._errors.AuthenticationError as e:
            raise LLMAuthorizationError(self._config.id, self._config.model, str(e)) from e
        except self._errors.RateLimitError as e:
            raise LLMRateLimitError(self._config.id, self._config.model, str(e)) from e
        except self._errors.APIError as e:
            raise LLMRequestFailedError(self._config.id, self._config.model, str(e)) from e
        except Exception as e:  # transport-уровень: сеть, DNS, отвалившийся локальный сервер
            raise LLMRequestFailedError(self._config.id, self._config.model, str(e)) from e

        if not response.choices:
            raise LLMRequestFailedError(
                self._config.id, self._config.model, "провайдер вернул пустой список вариантов"
            )

        return response.choices[0].message.content or ""


class OpenAISDKSessionFactory(LLMSessionFactoryProtocol):
    """
    Фабрика сессий поверх пакета `openai`.

    SDK импортируется лениво: игра должна запускаться и без установленного
    пакета, пока игрок не настроил ни одной модели.
    """

    @asynccontextmanager
    async def open_session(
        self, config: LLMProviderConfig, api_key: Optional[str]
    ) -> AsyncIterator[ChatSessionProtocol]:
        """
        Открывает сессию на один запрос и гарантированно закрывает соединение.
        """
        try:
            import openai
            from openai import AsyncOpenAI
        except ImportError as e:
            raise LLMRequestFailedError(
                config.id,
                config.model,
                "не установлен пакет 'openai' (pip install openai)",
            ) from e

        sdk_client = AsyncOpenAI(
            # Совместимые локальные серверы ключ игнорируют, но SDK требует непустую строку
            api_key=api_key or "no-key-required",
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
        )
        try:
            yield _OpenAISDKSession(sdk_client, config, errors=openai)
        finally:
            await sdk_client.close()


# ==================================================================
# КЛИЕНТ
# ==================================================================


class OpenAICompatibleClient(LLMClientProtocol):
    """
    Клиент одного провайдера: собирает сообщения, берет ключ, открывает сессию
    на запрос и разбирает ответ.

    Сессия живет ровно один вызов: ключ мог смениться ротацией или настройками
    между двумя обращениями, а держать открытое соединение на всю партию незачем.
    """

    def __init__(
        self,
        config: LLMProviderConfig,
        key_manager: Optional[ApiKeyManager] = None,
        session_factory: Optional[LLMSessionFactoryProtocol] = None,
    ) -> None:
        self._config = config
        self._keys = key_manager
        self._sessions = session_factory or OpenAISDKSessionFactory()

    @property
    def config(self) -> LLMProviderConfig:
        return self._config

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Генерация свободного художественного текста (письма, летописи, слухи).
        """
        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_prompt),
            ChatMessage(role=ChatRole.USER, content=user_prompt),
        ]
        return await self._complete(messages, temperature=temperature, max_tokens=max_tokens)

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        temperature: float = 0.6,
    ) -> T:
        """
        Генерация строго валидированного JSON по Pydantic-модели.

        Схема уходит провайдеру машинным способом (response_format), а для
        совместимых серверов, которые его не поддерживают, дублируется текстом
        в системном промпте. Если ответ все равно не проходит валидацию, модель
        переспрашивают с текстом ошибки - у локальных моделей это основной путь
        к валидному ответу.
        """
        schema = _harden_schema(response_model.model_json_schema())
        response_format = self._build_response_format(response_model.__name__, schema)

        system_content = system_prompt
        if not self._config.supports_json_schema:
            system_content = (
                f"{system_prompt}\n\n"
                "Ответь строго одним JSON-объектом по схеме ниже, без пояснений и markdown.\n"
                f"{json.dumps(schema, ensure_ascii=False)}"
            )

        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_content),
            ChatMessage(role=ChatRole.USER, content=user_prompt),
        ]

        last_error = ""
        for attempt in range(self._config.structured_retries + 1):
            raw = await self._complete(
                messages, temperature=temperature, response_format=response_format
            )
            try:
                return response_model.model_validate_json(_extract_json(raw))
            except (ValidationError, ValueError) as e:
                last_error = str(e)
                main_logger.warning(
                    f"[LLM] Модель '{self._config.model}' вернула невалидный JSON "
                    f"(попытка {attempt + 1}): {last_error}"
                )
                messages = [
                    *messages,
                    ChatMessage(role=ChatRole.ASSISTANT, content=raw),
                    ChatMessage(
                        role=ChatRole.USER,
                        content=(
                            "Твой ответ не прошел валидацию схемы. Ошибка:\n"
                            f"{last_error}\n"
                            "Верни исправленный JSON-объект и ничего кроме него."
                        ),
                    ),
                ]

        raise LLMResponseFormatError(self._config.model, last_error)

    # ==================================================================
    # СЛУЖЕБНОЕ
    # ==================================================================

    async def _complete(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Выполняет один запрос и попутно ведет учет здоровья ключа.
        """
        api_key = self._acquire_key()

        try:
            async with self._sessions.open_session(self._config, api_key) as session:
                answer = await session.complete(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
        except LLMAuthorizationError:
            self._report(lambda keys, key: keys.report_rejected(self._config.id, key), api_key)
            raise
        except LLMRateLimitError:
            self._report(
                lambda keys, key: keys.report_rate_limited(self._config.id, key), api_key
            )
            raise

        self._report(lambda keys, key: keys.report_success(self._config.id, key), api_key)
        return answer

    def _acquire_key(self) -> Optional[str]:
        """
        Берет ключ у менеджера. Провайдеру без ключа (локальная модель) ключ не нужен.
        """
        if not self._config.requires_api_key or self._keys is None:
            return None
        return self._keys.get_key(self._config.id)

    def _report(self, report: Any, api_key: Optional[str]) -> None:
        if self._keys is not None and api_key is not None:
            report(self._keys, api_key)

    def _build_response_format(self, name: str, schema: dict[str, Any]) -> dict[str, Any]:
        if not self._config.supports_json_schema:
            # Минимальный общий знаменатель: просто попросить JSON
            return {"type": "json_object"}

        return {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "schema": schema,
                "strict": self._config.strict_json_schema,
            },
        }


def _harden_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Дополняет схему Pydantic запретом лишних полей.

    Строгий режим провайдеров требует явного additionalProperties: false у
    каждого объекта, а Pydantic его не проставляет.
    """
    if schema.get("type") == "object":
        schema.setdefault("additionalProperties", False)

    for key in ("properties", "$defs", "definitions"):
        for value in schema.get(key, {}).values():
            if isinstance(value, dict):
                _harden_schema(value)

    for key in ("items", "additionalItems"):
        value = schema.get(key)
        if isinstance(value, dict):
            _harden_schema(value)

    for key in ("anyOf", "oneOf", "allOf"):
        for value in schema.get(key, []):
            if isinstance(value, dict):
                _harden_schema(value)

    return schema


def _extract_json(raw: str) -> str:
    """
    Выковыривает JSON из ответа модели, снимая markdown-обертку, если она есть.
    """
    fenced = _JSON_FENCE.match(raw)
    return fenced.group(1) if fenced else raw.strip()
