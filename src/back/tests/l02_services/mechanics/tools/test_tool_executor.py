"""
Тесты диспетчера навыков: поиск обработчика, разбор аргументов по схеме,
изоляция ошибок и нормализация результата.

Исполнитель - последний рубеж между фантазией модели и сервером: что бы ни
приехало, наружу обязан выйти `ToolResult`, а не исключение.
"""

import pytest
from pydantic import BaseModel, Field

from src.back.l01_domain.exceptions.base import DomainError
from src.back.l01_domain.llm.models.tools import ToolDefinition, ToolResult
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.tests.l02_services.fakes import tool_call


class MarchParams(BaseModel):
    """Параметры-образец для тестов диспетчера."""

    army_id: str = Field(..., min_length=1)
    haste: int = Field(default=0, ge=0, le=3)


MARCH = ToolDefinition(
    name="march",
    description="Отправить армию в поход.",
    parameters_model=MarchParams,
)

MARCH_CALL = tool_call("march", army_id="army_1", haste=2)


@pytest.fixture
def bare_context(world) -> ToolExecutionContext:
    return ToolExecutionContext(world_state=world, caller_faction_id="humans")


@pytest.fixture
def register(bare_context):
    """Собирает исполнителя с одним навыком и заданным обработчиком."""

    def _register(handler) -> ToolExecutor:
        executor = ToolExecutor()
        executor.register_handler(MARCH, handler)
        return executor

    return _register


# ==================================================================
# РЕЕСТР ОБРАБОТЧИКОВ
# ==================================================================


class TestRegistry:
    async def test_registered_tool_is_visible(self, register):
        async def handler(params, ctx):
            return "ок"

        executor = register(handler)

        assert executor.has_handler("march") is True
        assert executor.get_definition("march") is MARCH
        assert executor.list_definitions() == [MARCH]

    def test_unknown_tool_is_not_registered(self):
        executor = ToolExecutor()

        assert executor.has_handler("march") is False
        assert executor.get_definition("march") is None
        assert executor.list_definitions() == []

    async def test_reregistration_replaces_the_handler(self, register, bare_context):
        """Навык подключает ровно один набор обработчиков - последний."""

        async def first(params, ctx):
            return "первый"

        async def second(params, ctx):
            return "второй"

        executor = register(first)
        executor.register_handler(MARCH, second)

        result = await executor.execute(MARCH_CALL, bare_context)

        assert result.output == "второй"
        assert executor.list_definitions() == [MARCH]


# ==================================================================
# ИСПОЛНЕНИЕ ВЫЗОВА
# ==================================================================


class TestExecute:
    async def test_arguments_arrive_typed(self, register, bare_context):
        seen: dict = {}

        async def handler(params: MarchParams, ctx: ToolExecutionContext):
            seen["params"] = params
            seen["ctx"] = ctx
            return "ок"

        await register(handler).execute(MARCH_CALL, bare_context)

        assert isinstance(seen["params"], MarchParams)
        assert seen["params"].army_id == "army_1"
        assert seen["params"].haste == 2
        assert seen["ctx"] is bare_context

    async def test_result_names_the_call_and_the_tool(self, register, bare_context):
        async def handler(params, ctx):
            return "ок"

        result = await register(handler).execute(MARCH_CALL, bare_context)

        assert result.success is True
        assert result.call_id == MARCH_CALL.id
        assert result.tool_name == "march"

    async def test_unknown_tool_is_an_honest_refusal(self, register, bare_context):
        """
        Модель выдумала навык: сервер отвечает отказом, а не падает, - модель
        прочитает его и попробует иначе.
        """

        async def handler(params, ctx):
            return "ок"

        result = await register(handler).execute(
            tool_call("annex_everything"), bare_context
        )

        assert result.success is False
        assert "annex_everything" in result.error
        assert result.tool_name == "annex_everything"

    async def test_arguments_beyond_the_schema_are_rejected(self, register, bare_context):
        called = False

        async def handler(params, ctx):
            nonlocal called
            called = True
            return "ок"

        result = await register(handler).execute(
            tool_call("march", haste=99), bare_context
        )

        assert result.success is False
        assert "параметры" in result.error.lower()
        assert called is False, "Обработчик не должен видеть невалидные аргументы"

    async def test_domain_error_becomes_a_reason_for_the_model(
        self, register, bare_context
    ):
        """
        Мир не принял действие по правилам игры: это не сбой сервера, а ответ,
        по которому модель может скорректировать план.
        """

        async def handler(params, ctx):
            raise DomainError("Армия связана боем.")

        result = await register(handler).execute(MARCH_CALL, bare_context)

        assert result.success is False
        assert result.error == "Армия связана боем."

    async def test_unexpected_error_does_not_escape_the_executor(
        self, register, bare_context
    ):
        """Ошибка в обработчике не должна ронять ход целиком."""

        async def handler(params, ctx):
            raise RuntimeError("делить на ноль")

        result = await register(handler).execute(MARCH_CALL, bare_context)

        assert result.success is False
        assert "делить на ноль" in result.error


# ==================================================================
# НОРМАЛИЗАЦИЯ ОТВЕТА ОБРАБОТЧИКА
# ==================================================================


class TestNormalization:
    async def test_plain_string_becomes_the_output(self, register, bare_context):
        async def handler(params, ctx):
            return "Армия выступила."

        result = await register(handler).execute(MARCH_CALL, bare_context)

        assert result.success is True
        assert result.output == "Армия выступила."
        assert result.data is None

    async def test_pair_carries_words_and_data(self, register, bare_context):
        async def handler(params, ctx):
            return "Армия выступила.", {"army_id": "army_1"}

        result = await register(handler).execute(MARCH_CALL, bare_context)

        assert result.output == "Армия выступила."
        assert result.data == {"army_id": "army_1"}

    async def test_ready_result_passes_through_untouched(self, register, bare_context):
        """Обработчик вправе сам решить, что вызов провалился."""
        prepared = ToolResult(
            call_id="call_own",
            tool_name="march",
            success=False,
            error="Своя причина отказа.",
        )

        async def handler(params, ctx):
            return prepared

        result = await register(handler).execute(MARCH_CALL, bare_context)

        assert result is prepared

    async def test_silent_handler_still_reports_success(self, register, bare_context):
        async def handler(params, ctx):
            return None

        result = await register(handler).execute(MARCH_CALL, bare_context)

        assert result.success is True
        assert result.output


# ==================================================================
# ПАКЕТНОЕ ИСПОЛНЕНИЕ
# ==================================================================


class TestExecuteMany:
    async def test_calls_are_executed_in_order(self, register, bare_context):
        order: list[str] = []

        async def handler(params: MarchParams, ctx):
            order.append(params.army_id)
            return f"Армия {params.army_id} выступила."

        results = await register(handler).execute_many(
            [
                tool_call("march", army_id="army_1"),
                tool_call("march", army_id="army_2"),
                tool_call("march", army_id="army_3"),
            ],
            bare_context,
        )

        assert order == ["army_1", "army_2", "army_3"]
        assert [r.output for r in results] == [
            "Армия army_1 выступила.",
            "Армия army_2 выступила.",
            "Армия army_3 выступила.",
        ]

    async def test_failed_call_does_not_stop_the_rest(self, register, bare_context):
        """
        Модель отдает приказы пачкой: неудача одного не повод отменять
        остальные - каждый получит свой вердикт.
        """

        async def handler(params: MarchParams, ctx):
            if params.army_id == "army_2":
                raise DomainError("Армия связана боем.")
            return "Армия выступила."

        results = await register(handler).execute_many(
            [
                tool_call("march", army_id="army_1"),
                tool_call("march", army_id="army_2"),
                tool_call("march", army_id="army_3"),
            ],
            bare_context,
        )

        assert [r.success for r in results] == [True, False, True]
        assert results[1].error == "Армия связана боем."

    async def test_empty_batch_is_not_an_error(self, register, bare_context):
        async def handler(params, ctx):
            return "ок"

        assert await register(handler).execute_many([], bare_context) == []
