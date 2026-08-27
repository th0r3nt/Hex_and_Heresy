"""
Тесты исполнителя действий советника.

Исполнитель - это заглушка до появления навыков Function Calling, но у нее
есть свой контракт: наружу он не бросает ничего, а о каждом намерении
отчитывается статусом. Именно на этот отчет опирается интерфейс, решая,
показать игроку выполненный совет или непримененный.
"""

import pytest

from src.back.l01_domain.exceptions.factions import InsufficientResourcesError
from src.back.l01_domain.factions.models.advisor import (
    AdvisorAction,
    AdvisorActionStatus,
)
from src.back.l02_services.mechanics.advisor.actions import AdvisorActionExecutor

RAISE_TAXES = AdvisorAction(
    tool_name="change_taxes", arguments={"percent": 10, "action": "increase"}
)


@pytest.fixture
def executor() -> AdvisorActionExecutor:
    return AdvisorActionExecutor()


# ==================================================================
# ПУСТОЙ РЕЕСТР: СОСТОЯНИЕ ДО НАВЫКОВ
# ==================================================================


class TestEmptyRegistry:
    def test_fresh_executor_knows_no_skills(self, executor):
        """Схемы навыков еще не написаны - реестр пуст."""
        assert executor.known_tools == []
        assert executor.supports("change_taxes") is False

    @pytest.mark.asyncio
    async def test_unknown_skill_is_reported_not_executed(self, executor, world):
        """
        Игрок должен увидеть, что совет не применен, а не решить, что налоги
        уже подняты.
        """
        outcome = await executor.execute(world, "humans", RAISE_TAXES)

        assert outcome.status == AdvisorActionStatus.NOT_SUPPORTED
        assert outcome.is_executed is False
        assert "change_taxes" in outcome.detail

    @pytest.mark.asyncio
    async def test_unknown_skill_does_not_raise(self, executor, world):
        """Красный экран вместо реплики советника игрок получить не должен."""
        outcomes = await executor.execute_all(world, "humans", [RAISE_TAXES])

        assert len(outcomes) == 1
        assert outcomes[0].status == AdvisorActionStatus.NOT_SUPPORTED


# ==================================================================
# ПОДКЛЮЧЕННЫЕ НАВЫКИ
# ==================================================================


class TestRegisteredHandlers:
    @pytest.mark.asyncio
    async def test_handler_receives_world_faction_and_arguments(self, executor, world):
        """
        Контракт обработчика: мир, фракция-заказчик и разобранные аргументы
        навыка. На него будет опираться этап Function Calling.
        """
        seen: list[tuple] = []

        async def handler(world_state, faction_id, arguments) -> str:
            seen.append((world_state, faction_id, arguments))
            return "Налог поднят на 10%."

        executor.register("change_taxes", handler)
        outcome = await executor.execute(world, "humans", RAISE_TAXES)

        assert seen == [(world, "humans", RAISE_TAXES.arguments)]
        assert outcome.status == AdvisorActionStatus.EXECUTED
        assert outcome.detail == "Налог поднят на 10%."

    def test_registration_is_visible_in_the_registry(self, executor):
        async def handler(world_state, faction_id, arguments) -> str:
            return ""

        executor.register("change_taxes", handler)

        assert executor.supports("change_taxes") is True
        assert executor.known_tools == ["change_taxes"]

    @pytest.mark.asyncio
    async def test_second_registration_replaces_the_first(self, executor, world):
        async def old(world_state, faction_id, arguments) -> str:
            return "старый"

        async def new(world_state, faction_id, arguments) -> str:
            return "новый"

        executor.register("change_taxes", old)
        executor.register("change_taxes", new)

        outcome = await executor.execute(world, "humans", RAISE_TAXES)

        assert outcome.detail == "новый"
        assert executor.known_tools == ["change_taxes"]

    @pytest.mark.asyncio
    async def test_world_refusal_becomes_a_failed_outcome(self, executor, world):
        """
        Домен отверг действие (не хватило казны) - это ответ игроку,
        а не падение запроса.
        """

        async def handler(world_state, faction_id, arguments) -> str:
            raise InsufficientResourcesError("gold", 500.0, 10.0, "humans")

        executor.register("hire_guards", handler)

        outcome = await executor.execute(
            world, "humans", AdvisorAction(tool_name="hire_guards")
        )

        assert outcome.status == AdvisorActionStatus.FAILED
        assert outcome.is_executed is False
        assert "gold" in outcome.detail

    @pytest.mark.asyncio
    async def test_actions_are_executed_in_order(self, executor, world):
        """Порядок намерений советника сохраняется: сначала налог, потом стража."""
        called: list[str] = []

        async def handler(world_state, faction_id, arguments) -> str:
            called.append(arguments["mark"])
            return arguments["mark"]

        executor.register("first", handler)
        executor.register("second", handler)

        outcomes = await executor.execute_all(
            world,
            "humans",
            [
                AdvisorAction(tool_name="first", arguments={"mark": "налог"}),
                AdvisorAction(tool_name="second", arguments={"mark": "стража"}),
            ],
        )

        assert called == ["налог", "стража"]
        assert [outcome.detail for outcome in outcomes] == ["налог", "стража"]

    @pytest.mark.asyncio
    async def test_unsupported_action_does_not_stop_the_rest(self, executor, world):
        """Один неизвестный навык не отменяет остальные намерения советника."""

        async def handler(world_state, faction_id, arguments) -> str:
            return "сделано"

        executor.register("known", handler)

        outcomes = await executor.execute_all(
            world,
            "humans",
            [AdvisorAction(tool_name="unknown"), AdvisorAction(tool_name="known")],
        )

        assert [outcome.status for outcome in outcomes] == [
            AdvisorActionStatus.NOT_SUPPORTED,
            AdvisorActionStatus.EXECUTED,
        ]
