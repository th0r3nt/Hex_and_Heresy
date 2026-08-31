"""
Тесты вызова навыков (Function Calling) у исполнителя запросов к LLM:
подготовка схем для провайдера, разбор пришедших вызовов и поведение
транспорта при сбоях.

Здесь проходит граница доверия: все, что приехало от провайдера, - сырые
строки, и превратить их в доменные `ToolCall` обязан именно этот слой.
"""

from types import SimpleNamespace
from typing import Any, Optional

import pytest

from src.back.l01_domain.exceptions.llm import (
    LLMAuthorizationError,
    LLMRequestFailedError,
)
from src.back.l01_domain.llm.models.tools import ToolCall
from src.back.l01_domain.llm.tools.catalog import Toolset, get_toolset
from src.back.l01_domain.llm.tools.definitions.general import REPLY
from src.back.l01_domain.llm.tools.definitions.strategic import ORDER_ARMY_MARCH, SET_TAX_RATE
from src.back.l01_domain.llm.tools.schemas.strategic import SetTaxRateParams
from src.back.l03_infrastructure.llm.executor import LLMExecutor
from src.back.l03_infrastructure.llm.keys.rotator import APIKeyRotator

TOOLS = [SET_TAX_RATE, ORDER_ARMY_MARCH]


def raw_call(name: str, arguments: str, call_id: Optional[str] = "call_provider_1") -> Any:
    """Вызов навыка так, как его отдает SDK провайдера: строкой аргументов."""
    function = SimpleNamespace(name=name, arguments=arguments)
    if call_id is None:
        return SimpleNamespace(function=function)
    return SimpleNamespace(id=call_id, function=function)


@pytest.fixture
def build(llm_fakes):
    """Собирает исполнителя с фейковым клиентом по сценарию ответов."""

    def _build(script, keys=("key-alpha",), max_retries=2, **config_overrides):
        rotator = APIKeyRotator(provider_id="test_provider", keys=list(keys))
        client = llm_fakes.Client(rotator, list(script), max_retries=max_retries)
        executor = LLMExecutor(
            config=llm_fakes.config(max_retries=max_retries, **config_overrides),
            client=client,
        )
        return executor, client

    return _build


@pytest.fixture
def answer(llm_fakes):
    """Ответ модели со свободным текстом и вызовами навыков."""

    def _answer(content: str = "", *calls: Any) -> Any:
        return llm_fakes.completion(content, tool_calls=list(calls) or None)

    return _answer


# ==================================================================
# ПОДГОТОВКА ЗАПРОСА
# ==================================================================


class TestRequest:
    async def test_tools_are_sent_as_function_schemas(self, build, answer):
        executor, client = build([answer("")])

        await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        sent = client.calls[0]["tools"]
        assert [tool["function"]["name"] for tool in sent] == [
            "set_tax_rate",
            "order_army_march",
        ]
        assert sent[0]["type"] == "function"
        assert "rate" in sent[0]["function"]["parameters"]["properties"]

    async def test_tool_choice_is_auto_by_default(self, build, answer):
        executor, client = build([answer("")])

        await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert client.calls[0]["tool_choice"] == "auto"

    async def test_forced_tool_choice_reaches_the_provider(self, build, answer):
        """Иногда сцена требует ответа навыком: выбор передают явно."""
        executor, client = build([answer("")])
        choice = {"type": "function", "function": {"name": "set_tax_rate"}}

        await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS, tool_choice=choice
        )

        assert client.calls[0]["tool_choice"] == choice

    async def test_empty_toolset_does_not_send_tool_fields(self, build, answer):
        """
        Роль без навыков - обычный разговор: пустые поля провайдеру не нужны,
        а некоторые совместимые API на них и вовсе ругаются.
        """
        executor, client = build([answer("Лорд молчит.")])

        await executor.generate_with_tools(system_prompt="s", user_prompt="u", tools=[])

        assert "tools" not in client.calls[0]
        assert "tool_choice" not in client.calls[0]

    async def test_prompts_and_temperature_are_forwarded(self, build, answer):
        executor, client = build([answer("")])

        await executor.generate_with_tools(
            system_prompt="Ты — лорд.",
            user_prompt="Ответь послу.",
            tools=TOOLS,
            temperature=0.3,
        )

        assert client.calls[0]["messages"] == [
            {"role": "system", "content": "Ты — лорд."},
            {"role": "user", "content": "Ответь послу."},
        ]
        assert client.calls[0]["temperature"] == 0.3

    async def test_lenient_provider_gets_a_soft_schema(self, build, answer):
        """По умолчанию строгий режим схем выключен: его держат не все API."""
        executor, client = build([answer("")])

        await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=[SET_TAX_RATE]
        )

        function = client.calls[0]["tools"][0]["function"]
        assert function["strict"] is False
        assert "additionalProperties" not in function["parameters"]

    async def test_strict_provider_gets_a_hardened_schema(self, build, answer):
        executor, client = build([answer("")], strict_json_schema=True)

        await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=[SET_TAX_RATE]
        )

        function = client.calls[0]["tools"][0]["function"]
        assert function["strict"] is True
        assert function["parameters"]["additionalProperties"] is False

    async def test_whole_scene_toolset_is_accepted(self, build, answer):
        """Реестр наборов отдает готовые списки - они должны уезжать как есть."""
        executor, client = build([answer("")])
        toolset = get_toolset(Toolset.LORD_AUDIENCE)

        await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=toolset
        )

        assert len(client.calls[0]["tools"]) == len(toolset)


# ==================================================================
# РАЗБОР ОТВЕТА
# ==================================================================


class TestParsing:
    async def test_call_becomes_a_domain_tool_call(self, build, answer):
        executor, _ = build([answer("", raw_call("set_tax_rate", '{"rate": 1.2}'))])

        content, calls = await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert content == ""
        assert len(calls) == 1
        assert isinstance(calls[0], ToolCall)
        assert calls[0].id == "call_provider_1"
        assert calls[0].name == "set_tax_rate"
        assert calls[0].arguments == {"rate": 1.2}
        assert calls[0].raw_arguments == '{"rate": 1.2}'

    async def test_parsed_call_is_ready_for_the_service_layer(self, build, answer):
        """Разобранный вызов обязан ложиться в доменную схему без доработки."""
        executor, _ = build([answer("", raw_call("set_tax_rate", '{"rate": 1.5}'))])

        _content, calls = await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert calls[0].parse_arguments(SetTaxRateParams).rate == 1.5

    async def test_words_and_a_call_arrive_together(self, build, answer):
        executor, _ = build(
            [answer("Поднимаю сбор.", raw_call("set_tax_rate", '{"rate": 1.1}'))]
        )

        content, calls = await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert content == "Поднимаю сбор."
        assert calls[0].name == "set_tax_rate"

    async def test_parallel_calls_keep_their_order(self, build, answer):
        """
        Модель вправе отдать несколько приказов за один ход - порядок важен:
        исполнитель применяет их по очереди.
        """
        executor, _ = build(
            [
                answer(
                    "",
                    raw_call("set_tax_rate", '{"rate": 1.1}', "call_1"),
                    raw_call("order_army_march", '{"army_id": "a1"}', "call_2"),
                    raw_call("set_tax_rate", '{"rate": 0.9}', "call_3"),
                )
            ]
        )

        _content, calls = await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert [call.id for call in calls] == ["call_1", "call_2", "call_3"]
        assert [call.name for call in calls] == [
            "set_tax_rate",
            "order_army_march",
            "set_tax_rate",
        ]

    async def test_silence_of_the_model_is_an_empty_list(self, build, answer):
        executor, _ = build([answer("Лорд просто слушает.")])

        content, calls = await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert content == "Лорд просто слушает."
        assert calls == []

    async def test_missing_content_becomes_an_empty_string(self, build, llm_fakes):
        """Ответ одним навыком без слов - обычное дело для провайдера."""
        completion = llm_fakes.completion(None, tool_calls=[raw_call("set_tax_rate", "{}")])
        executor, _ = build([completion])

        content, calls = await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert content == ""
        assert len(calls) == 1


# ==================================================================
# БРАК В ОТВЕТЕ ПРОВАЙДЕРА
# ==================================================================


class TestBrokenArguments:
    async def test_broken_json_leaves_the_call_without_arguments(self, build, answer):
        """
        Ронять такт из-за оборванной строки нельзя: вызов доезжает пустым,
        а разбор по схеме на сервисном слое честно его отвергнет.
        """
        executor, _ = build([answer("", raw_call("set_tax_rate", '{"rate": 1.2'))])

        _content, calls = await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert calls[0].arguments == {}

    async def test_broken_json_keeps_the_original_string(self, build, answer):
        """Сырая строка нужна для логов: по ней видно, что именно сломалось."""
        executor, _ = build([answer("", raw_call("set_tax_rate", "не json"))])

        _content, calls = await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert calls[0].raw_arguments == "не json"

    @pytest.mark.parametrize("payload", ["[1, 2]", '"строка"', "42", "null"])
    async def test_arguments_that_are_not_an_object_are_dropped(
        self, build, answer, payload
    ):
        """Аргументы навыка - всегда объект: список или число схеме не пара."""
        executor, _ = build([answer("", raw_call("set_tax_rate", payload))])

        _content, calls = await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert calls[0].arguments == {}

    async def test_call_without_an_identifier_gets_a_name_based_one(self, build, answer):
        """
        Идентификатор нужен, чтобы связать результат с вызовом. Совместимые
        API его иногда не присылают.
        """
        executor, _ = build([answer("", raw_call("set_tax_rate", "{}", call_id=None))])

        _content, calls = await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert calls[0].id == "call_set_tax_rate"

    async def test_unknown_tool_name_is_passed_on_as_is(self, build, answer):
        """
        Отсеивать выдуманные навыки - работа исполнителя сервисного слоя:
        он знает, что зарегистрировано, и умеет ответить модели отказом.
        """
        executor, _ = build([answer("", raw_call("annex_everything", "{}"))])

        _content, calls = await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert calls[0].name == "annex_everything"


# ==================================================================
# СБОИ ТРАНСПОРТА
# ==================================================================


class TestTransportFailures:
    async def test_rate_limit_is_retried_on_another_key(
        self, build, answer, llm_fakes, sleeps, clock
    ):
        """Лимит одного ключа не должен стоить сцене вызова навыка."""
        executor, client = build(
            [
                llm_fakes.rate_limit_error(),
                answer("", raw_call("set_tax_rate", '{"rate": 1.2}')),
            ],
            keys=("key-alpha", "key-bravo"),
        )

        _content, calls = await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert calls[0].name == "set_tax_rate"
        assert len(client.calls) == 2
        assert client.used_keys == ["key-alpha", "key-bravo"]

    async def test_tools_are_resent_on_every_retry(
        self, build, answer, llm_fakes, sleeps, clock
    ):
        """Повторный запрос без навыков вернул бы пустую болтовню."""
        executor, client = build(
            [llm_fakes.api_error(), answer("", raw_call("set_tax_rate", "{}"))],
        )

        await executor.generate_with_tools(
            system_prompt="s", user_prompt="u", tools=TOOLS
        )

        assert [len(call["tools"]) for call in client.calls] == [2, 2]

    async def test_timeouts_beyond_the_limit_are_reported(
        self, build, llm_fakes, sleeps, clock
    ):
        executor, _ = build([llm_fakes.timeout_error()] * 3, max_retries=2)

        with pytest.raises(LLMRequestFailedError):
            await executor.generate_with_tools(
                system_prompt="s", user_prompt="u", tools=TOOLS
            )

    async def test_rejected_key_is_reported_as_an_authorization_error(
        self, build, llm_fakes, sleeps, clock
    ):
        executor, _ = build([llm_fakes.auth_error()], keys=("key-alpha",))

        with pytest.raises(LLMAuthorizationError):
            await executor.generate_with_tools(
                system_prompt="s", user_prompt="u", tools=[REPLY]
            )
