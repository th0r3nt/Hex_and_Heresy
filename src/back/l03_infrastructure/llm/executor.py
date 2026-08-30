"""
Исполнитель прикладных задач языковых моделей.

Реализует `LLMClientProtocol`:
- Генерацию свободного художественного текста;
- Валидацию структурированного JSON через Pydantic с диалоговым исправлением ошибок;
- Вызов инструментов (Function Calling / Tools) и парсинг аргументов.
"""

import json
import re
from typing import Any, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError

from src.back.l01_domain.exceptions.llm import LLMResponseFormatError
from src.back.l01_domain.llm.models.provider import LLMProviderConfig
from src.back.l01_domain.llm.models.tools import ToolCall, ToolDefinition
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l03_infrastructure.llm.client import LLMClient
from src.back.utils.logger import main_logger

T = TypeVar("T", bound=BaseModel)

# Регулярное выражение для извлечения JSON из markdown-блоков (```json ... ```)
_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class LLMExecutor(LLMClientProtocol):
    """
    Прикладной исполнитель обращений к языковой модели.
    Делегирует сетевой транспорт клиенту LLMClient.
    """

    def __init__(self, config: LLMProviderConfig, client: LLMClient) -> None:
        self.config = config
        self.client = client

    # =========================================================================
    # Генерация текста
    # =========================================================================

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
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await self.client.create_chat_completion(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    # =========================================================================
    # Структурированная генерация (Pydantic / Structured Outputs)
    # =========================================================================

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        temperature: float = 0.6,
    ) -> T:
        """
        Генерация строго валидированного JSON по Pydantic-модели с циклом авто-исправления.
        """
        schema = self._harden_schema(response_model.model_json_schema())
        response_format = self._build_response_format(response_model.__name__, schema)

        system_content = system_prompt
        if not self.config.supports_json_schema:
            system_content = (
                f"{system_prompt}\n\n"
                "Ответь строго одним JSON-объектом по схеме ниже, без пояснений и markdown.\n"
                f"{json.dumps(schema, ensure_ascii=False)}"
            )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt},
        ]

        last_error = ""
        for attempt in range(self.config.structured_retries + 1):
            response = await self.client.create_chat_completion(
                model=self.config.model,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
            )

            raw_content = response.choices[0].message.content or ""
            clean_json = self._extract_json(raw_content)

            try:
                return response_model.model_validate_json(clean_json)
            except (ValidationError, ValueError) as err:
                last_error = str(err)
                main_logger.warning(
                    f"[LLM] Модель '{self.config.model}' вернула невалидный JSON "
                    f"(попытка {attempt + 1}/{self.config.structured_retries + 1}): {last_error}"
                )

                # Добавляем ошибку в историю диалога для исправления моделью
                messages.append({"role": "assistant", "content": raw_content})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Твой ответ не прошел валидацию схемы. Ошибка:\n{last_error}\n"
                            "Верни исправленный JSON-объект без пояснений."
                        ),
                    }
                )

        raise LLMResponseFormatError(self.config.model, last_error)

    # =========================================================================
    # Вызов инструментов (Function Calling / Tools)
    # =========================================================================

    async def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
        temperature: float = 0.6,
        tool_choice: Optional[Union[str, dict[str, Any]]] = "auto",
    ) -> tuple[str, list[ToolCall]]:
        """
        Генерация с передачей доступных инструментов.
        Возвращает текстовый ответ модели и список распознанных вызовов инструментов.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        formatted_tools = [
            tool.to_openai_schema(strict=self.config.strict_json_schema) for tool in tools
        ]

        response = await self.client.create_chat_completion(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            tools=formatted_tools if formatted_tools else None,
            tool_choice=tool_choice if formatted_tools else None,
        )

        message = response.choices[0].message
        content = message.content or ""
        tool_calls = self._parse_tool_calls(message.tool_calls)

        return content, tool_calls

    # =========================================================================
    # Вспомогательные методы парсинга и форматирования схем
    # =========================================================================

    def _parse_tool_calls(self, raw_tool_calls: Any) -> list[ToolCall]:
        """
        Преобразует вызовы инструментов из SDK OpenAI в доменные модели ToolCall.
        """
        if not raw_tool_calls:
            return []

        parsed_calls: list[ToolCall] = []
        for raw in raw_tool_calls:
            func_name = getattr(raw.function, "name", "")
            raw_args = getattr(raw.function, "arguments", "{}")

            try:
                parsed_args = json.loads(raw_args)
                if not isinstance(parsed_args, dict):
                    parsed_args = {}
            except (json.JSONDecodeError, TypeError):
                parsed_args = {}

            parsed_calls.append(
                ToolCall(
                    id=getattr(raw, "id", f"call_{func_name}"),
                    name=func_name,
                    arguments=parsed_args,
                    raw_arguments=raw_args,
                )
            )

        return parsed_calls

    def _build_response_format(self, name: str, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Формирует параметр response_format для структурированного вывода.
        """
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

    def _harden_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Рекурсивно добавляет additionalProperties: false для строгого режима валидации схем.
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
        """
        Очищает текст от markdown-оберток JSON.
        """
        fenced = _JSON_FENCE.match(raw)
        return fenced.group(1) if fenced else raw.strip()
