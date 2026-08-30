"""
Тесты реестра наборов инструментов языковой модели.
"""

import pytest

from src.back.l01_domain.llm.models.tools import ToolDefinition
from src.back.l03_infrastructure.llm.tools import catalog
from src.back.l03_infrastructure.llm.tools.catalog import Toolset


def _names(tools: list[ToolDefinition]) -> set[str]:
    return {tool.name for tool in tools}


class TestToolsets:
    @pytest.mark.parametrize("name", list(Toolset))
    def test_every_toolset_resolves_to_non_empty_definitions(self, name: Toolset) -> None:
        tools = catalog.get_toolset(name)

        assert tools, f"Набор {name} пуст"
        assert all(isinstance(tool, ToolDefinition) for tool in tools)

    @pytest.mark.parametrize("name", list(Toolset))
    def test_toolset_has_no_duplicate_tools(self, name: Toolset) -> None:
        tools = catalog.get_toolset(name)
        assert len(_names(tools)) == len(tools), f"В наборе {name} есть повторы"

    def test_get_toolset_returns_a_copy(self) -> None:
        first = catalog.get_toolset(Toolset.TACTICAL_BATTLE)
        first.clear()

        assert catalog.get_toolset(Toolset.TACTICAL_BATTLE), "Реестр изменился извне"

    def test_strategic_turn_holds_map_skills_not_battle_orders(self) -> None:
        names = _names(catalog.get_toolset(Toolset.STRATEGIC_TURN))

        assert "order_army_march" in names
        assert "send_ambassador" in names  # внешняя политика - часть своего хода
        assert "order_squad_move" not in names
        assert "reply" not in names  # на своем ходу говорить некому
        assert "stay_silent" in names

    def test_tactical_battle_holds_only_squad_orders_and_silence(self) -> None:
        names = _names(catalog.get_toolset(Toolset.TACTICAL_BATTLE))

        assert names == {
            "order_squad_move",
            "order_squad_hold",
            "order_squad_reaction",
            "stay_silent",
        }

    def test_lord_audience_can_judge_but_not_dispatch_envoys(self) -> None:
        names = _names(catalog.get_toolset(Toolset.LORD_AUDIENCE))

        assert {"declare_war", "make_peace", "execute_ambassador", "reply"} <= names
        assert "send_ambassador" not in names
        assert "recall_ambassador" not in names

    def test_ambassador_mission_only_offers_and_talks(self) -> None:
        names = _names(catalog.get_toolset(Toolset.AMBASSADOR_MISSION))

        assert {"propose_trade", "make_peace", "reply", "stay_silent"} <= names
        assert "execute_ambassador" not in names
        assert "send_ambassador" not in names

    def test_writing_roles_have_no_generic_reply(self) -> None:
        assert "reply" not in _names(catalog.get_toolset(Toolset.CHRONICLE_WRITING))
        assert "record_chronicle" in _names(catalog.get_toolset(Toolset.CHRONICLE_WRITING))

    def test_advisor_council_pairs_proposal_with_reply(self) -> None:
        names = _names(catalog.get_toolset(Toolset.ADVISOR_COUNCIL))
        assert names == {"propose_advisor_action", "reply"}


class TestToolIndex:
    def test_all_tools_are_unique_and_cover_every_category(self) -> None:
        tools = catalog.all_tools()
        names = [tool.name for tool in tools]

        assert len(names) == len(set(names)), "В реестре есть навыки-дубликаты"

        for bundle in (
            catalog.GENERAL_TOOLS,
            catalog.STRATEGIC_TOOLS,
            catalog.TACTICAL_TOOLS,
            catalog.DIPLOMACY_TOOLS,
            catalog.GUNSMITH_TOOLS,
            catalog.GAME_MASTER_TOOLS,
            catalog.ADVISOR_TOOLS,
            catalog.CHRONICLER_TOOLS,
        ):
            assert _names(bundle) <= set(names)

    def test_every_toolset_tool_is_known_to_the_index(self) -> None:
        for name in Toolset:
            for tool in catalog.get_toolset(name):
                assert catalog.find_tool(tool.name) is tool

    def test_find_tool_misses_unknown_name(self) -> None:
        assert catalog.find_tool("summon_dragon") is None

    def test_find_tool_hits_known_name(self) -> None:
        found = catalog.find_tool("draft_blueprint")
        assert found is not None and found.name == "draft_blueprint"
