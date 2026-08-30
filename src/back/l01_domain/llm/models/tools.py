"""
Доменные сущности для вызова инструментов (Function Calling / Tools) языковыми моделями.
"""

from typing import Any, Optional, TypeVar
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.back.l01_domain.exceptions.llm import InvalidToolCallError

T = TypeVar("T", bound=BaseModel)


class ToolDefinition(BaseModel):
    """
    Доменное описание доступного инструмента (навыка) для языковой модели.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str = Field(
        ..., min_length=1, description="Уникальное имя функции (напр. 'order_army_march')"
    )
    description: str = Field(
        ..., min_length=1, description="Описание назначения инструмента для языковой модели"
    )
    parameters_model: type[BaseModel] = Field(
        ..., description="Pydantic-модель валидации входных аргументов инструмента"
    )

    def to_openai_schema(self, strict: bool = False) -> dict[str, Any]:
        """
        Формирует словарь в формате спецификации function calling для OpenAI API.
        """
        schema = self.parameters_model.model_json_schema()
        if strict:
            self._harden_schema(schema)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
                "strict": strict,
            },
        }

    @staticmethod
    def _harden_schema(schema: dict[str, Any]) -> None:
        """
        Добавляет additionalProperties: false для строгого режима валидации схем.
        """
        if schema.get("type") == "object":
            schema.setdefault("additionalProperties", False)
        for key in ("properties", "$defs", "definitions"):
            for value in schema.get(key, {}).values():
                if isinstance(value, dict):
                    ToolDefinition._harden_schema(value)
        for key in ("items", "additionalItems"):
            value = schema.get(key)
            if isinstance(value, dict):
                ToolDefinition._harden_schema(value)


class ToolCall(BaseModel):
    """
    Распознанный вызов инструмента от языковой модели.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        default_factory=lambda: f"call_{uuid4().hex[:8]}",
        description="Идентификатор вызова от провайдера API",
    )
    name: str = Field(..., min_length=1, description="Имя вызываемой функции")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Распарсенный словарь аргументов"
    )
    raw_arguments: str = Field(default="{}", description="Исходная JSON-строка аргументов")

    def parse_arguments(self, model: type[T]) -> T:
        """
        Валидирует переданные аргументы в целевую Pydantic-модель.
        """
        try:
            return model.model_validate(self.arguments)
        except ValidationError as err:
            raise InvalidToolCallError(self.name, str(err)) from err


class ToolResult(BaseModel):
    """
    Результат выполнения инструмента исполнителем сервисного слоя.
    """

    model_config = ConfigDict(frozen=True)

    call_id: str = Field(..., description="Идентификатор вызова ToolCall")
    tool_name: str = Field(..., description="Имя вызванного инструмента")
    success: bool = Field(default=True, description="Успешно ли выполнено действие")
    output: str = Field(
        default="", description="Человекочитаемый отчет о результате выполнения"
    )
    error: Optional[str] = Field(default=None, description="Текст ошибки при неудаче")
    data: Optional[dict[str, Any]] = Field(
        default=None, description="Дополнительные структурированные данные ответа"
    )
