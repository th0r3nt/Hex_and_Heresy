"""
Тесты доменных моделей вызова навыков: описание инструмента для модели,
разбор пришедшего вызова и результат его исполнения.

Это контракт между провайдером и сервисным слоем: схема уезжает в запрос,
а `ToolCall` приезжает обратно и обязан превратиться в типизированные
параметры или во внятную ошибку.
"""

from typing import Optional

import pytest
from pydantic import BaseModel, Field, ValidationError

from src.back.l01_domain.exceptions.llm import InvalidToolCallError
from src.back.l01_domain.llm.models.tools import ToolCall, ToolDefinition, ToolResult


class MarchParams(BaseModel):
    """Параметры-образец для тестов."""

    army_id: str = Field(..., min_length=1)
    haste: int = Field(default=0, ge=0, le=3)


class Squad(BaseModel):
    name: str


class Deployment(BaseModel):
    """Вложенная схема: проверяем рекурсивное ужесточение."""

    squads: list[Squad]
    reserve: Optional[Squad] = None


MARCH = ToolDefinition(
    name="march",
    description="Отправить армию в поход.",
    parameters_model=MarchParams,
)

DEPLOY = ToolDefinition(
    name="deploy",
    description="Расставить отряды.",
    parameters_model=Deployment,
)


# ==================================================================
# ОПИСАНИЕ НАВЫКА ДЛЯ МОДЕЛИ
# ==================================================================


class TestToolDefinition:
    def test_schema_follows_the_function_calling_shape(self):
        """Провайдер ждет ровно эту обертку вокруг JSON-схемы параметров."""
        schema = MARCH.to_openai_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "march"
        assert schema["function"]["description"] == "Отправить армию в поход."
        assert schema["function"]["parameters"]["properties"].keys() == {"army_id", "haste"}

    def test_lenient_schema_does_not_forbid_extra_properties(self):
        """
        Строгий режим поддерживают не все совместимые провайдеры, поэтому по
        умолчанию схема остается мягкой.
        """
        schema = MARCH.to_openai_schema()

        assert schema["function"]["strict"] is False
        assert "additionalProperties" not in schema["function"]["parameters"]

    def test_strict_schema_forbids_extra_properties(self):
        schema = MARCH.to_openai_schema(strict=True)

        assert schema["function"]["strict"] is True
        assert schema["function"]["parameters"]["additionalProperties"] is False

    def test_strict_schema_reaches_nested_models(self):
        """Вложенные объекты живут в $defs - их тоже нужно ужесточить."""
        parameters = DEPLOY.to_openai_schema(strict=True)["function"]["parameters"]

        assert parameters["additionalProperties"] is False
        assert parameters["$defs"]["Squad"]["additionalProperties"] is False

    def test_definition_is_frozen(self):
        """Реестр навыков раздает свои определения наружу и менять их нельзя."""
        with pytest.raises(ValidationError):
            MARCH.name = "another_name"

    def test_empty_name_or_description_is_rejected(self):
        with pytest.raises(ValidationError):
            ToolDefinition(name="", description="Пусто", parameters_model=MarchParams)

        with pytest.raises(ValidationError):
            ToolDefinition(name="march", description="", parameters_model=MarchParams)


# ==================================================================
# ВЫЗОВ НАВЫКА ОТ МОДЕЛИ
# ==================================================================


class TestToolCall:
    def test_arguments_become_a_typed_model(self):
        call = ToolCall(name="march", arguments={"army_id": "army_1", "haste": 2})

        params = call.parse_arguments(MarchParams)

        assert isinstance(params, MarchParams)
        assert params.army_id == "army_1"
        assert params.haste == 2

    def test_missing_defaults_are_filled_by_the_schema(self):
        call = ToolCall(name="march", arguments={"army_id": "army_1"})

        assert call.parse_arguments(MarchParams).haste == 0

    def test_broken_arguments_are_reported_as_an_invalid_call(self):
        """
        Модель выдумала параметры: сервисный слой должен получить доменную
        ошибку с именем навыка, а не сырую ошибку Pydantic.
        """
        call = ToolCall(name="march", arguments={"haste": 99})

        with pytest.raises(InvalidToolCallError) as error:
            call.parse_arguments(MarchParams)

        assert error.value.tool_name == "march"

    def test_call_without_arguments_gets_an_empty_pair(self):
        """Навык без параметров провайдер присылает с пустым телом."""
        call = ToolCall(name="stay_silent")

        assert call.arguments == {}
        assert call.raw_arguments == "{}"

    def test_call_gets_an_identifier_even_without_the_provider(self):
        """
        Идентификатор нужен, чтобы связать результат с вызовом: если провайдер
        его не прислал, вызов придумывает свой.
        """
        call = ToolCall(name="march")

        assert call.id.startswith("call_")
        assert ToolCall(name="march").id != call.id

    def test_call_is_frozen(self):
        call = ToolCall(name="march")

        with pytest.raises(ValidationError):
            call.name = "retreat"

    def test_nameless_call_is_rejected(self):
        with pytest.raises(ValidationError):
            ToolCall(name="")


# ==================================================================
# РЕЗУЛЬТАТ ИСПОЛНЕНИЯ
# ==================================================================


class TestToolResult:
    def test_result_is_successful_by_default(self):
        result = ToolResult(call_id="call_1", tool_name="march")

        assert result.success is True
        assert result.output == ""
        assert result.error is None
        assert result.data is None

    def test_failure_carries_the_reason_for_the_model(self):
        result = ToolResult(
            call_id="call_1",
            tool_name="march",
            success=False,
            error="Армия уже в походе.",
        )

        assert result.success is False
        assert result.error == "Армия уже в походе."

    def test_result_is_frozen(self):
        result = ToolResult(call_id="call_1", tool_name="march")

        with pytest.raises(ValidationError):
            result.success = False
