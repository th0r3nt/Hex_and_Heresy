"""
Тесты сборки диспетчера навыков: что из реестра доступно модели на самом деле.

Реестр наборов (домен) и обработчики (сервисы) пишутся порознь, и разъехаться
им нельзя: навык без обработчика - это обещание, которого сервер не выполнит.
"""

import pytest

from src.back.l01_domain.llm.tools.catalog import Toolset, all_tools, get_toolset
from src.back.l02_services.mechanics.tools.factory import build_tool_executor


def _names(executor) -> set[str]:
    return {definition.name for definition in executor.list_definitions()}


class TestFullAssembly:
    def test_every_tool_of_the_registry_has_a_handler(self, executor):
        """Модель не должна получить навык, который некому исполнить."""
        assert _names(executor) == {tool.name for tool in all_tools()}

    @pytest.mark.parametrize("scene", list(Toolset))
    def test_every_scene_is_fully_executable(self, executor, scene: Toolset):
        """
        Набор собирается под сцену: если хоть один его навык не подключен,
        модель упрется в отказ прямо посреди хода.
        """
        missing = [
            tool.name for tool in get_toolset(scene) if not executor.has_handler(tool.name)
        ]

        assert missing == []


class TestPartialAssembly:
    def test_without_facades_only_speech_and_battle_orders_remain(self):
        """
        Без фасадов исполнитель собирается пустым каркасом: речь и приказы
        отрядам ничего снаружи не требуют.
        """
        executor = build_tool_executor()

        assert _names(executor) == {
            "reply",
            "stay_silent",
            "order_squad_move",
            "order_squad_hold",
            "order_squad_reaction",
        }

    def test_facade_brings_only_its_own_tools(self, diplomacy_facade):
        executor = build_tool_executor(diplomacy_facade=diplomacy_facade)

        assert "declare_war" in _names(executor)
        assert "set_tax_rate" not in _names(executor)

    def test_missing_facade_turns_its_tools_into_an_honest_refusal(self, world, context):
        """
        Партия без летописца - не повод падать: навык просто не зарегистрирован,
        и модель получит отказ вместо исключения.
        """
        executor = build_tool_executor()

        assert executor.has_handler("record_chronicle") is False
