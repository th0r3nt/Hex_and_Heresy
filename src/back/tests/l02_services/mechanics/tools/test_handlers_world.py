"""
Интеграционные тесты навыков глобальной карты и тактического боя:
вызов модели обязан доехать до фасада хода и изменить мир.

Логика механик проверяется в tests/l02_services/turns/ - здесь только стык:
контекст сцены, параметры вызова и след, который остается в мире.
"""

from src.back.l01_domain.combat.constants import (
    SPEED_DEFENSE_PACE,
    ReactionType,
    TacticalMovementPace,
    TACTICAL_PACE_SPEEDS,
)
from src.back.l01_domain.factions.constants import MAX_TAX_RATE
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.tests.l02_services.fakes import tool_call


# ==================================================================
# ХОД ДЕРЖАВЫ
# ==================================================================


class TestStrategicHandlers:
    async def test_tax_rate_reaches_the_treasury(self, executor, world, context):
        result = await executor.execute(tool_call("set_tax_rate", rate=1.5), context())

        assert result.success is True
        assert world.get_faction("humans").tax_rate == 1.5
        assert result.data["tax_rate"] == 1.5

    async def test_tax_rate_beyond_the_scale_never_reaches_the_facade(
        self, executor, world, context
    ):
        """Схема - первый барьер: неигровую ставку отсекает разбор аргументов."""
        result = await executor.execute(
            tool_call("set_tax_rate", rate=MAX_TAX_RATE + 5), context()
        )

        assert result.success is False
        assert world.get_faction("humans").tax_rate != MAX_TAX_RATE + 5

    async def test_tool_of_a_faceless_caller_is_refused(self, executor, world, context):
        """
        Навык державы без самой державы бессмыслен: контекст сцены обязан
        назвать, кто говорит.
        """
        result = await executor.execute(
            tool_call("set_tax_rate", rate=1.5), context(caller_faction_id=None)
        )

        assert result.success is False
        assert "caller_faction_id" in result.error

    async def test_army_gets_its_route(self, executor, world, legion, context):
        result = await executor.execute(
            tool_call("order_army_march", army_id=legion.id, target_q=3, target_r=0),
            context(),
        )

        assert result.success is True
        assert legion.target_hex == HexCoordinates.from_axial(3, 0)
        assert legion.planned_path
        assert result.data["planned_path_length"] == len(legion.planned_path)

    async def test_march_of_an_unknown_army_is_refused_by_the_rules(
        self, executor, context
    ):
        """Доменная ошибка правил игры возвращается моделью как причина отказа."""
        result = await executor.execute(
            tool_call("order_army_march", army_id="army_never_was", target_q=1, target_r=0),
            context(),
        )

        assert result.success is False
        assert "не найдена" in result.error


# ==================================================================
# ПРИКАЗЫ В БОЮ
# ==================================================================


class TestTacticalHandlers:
    async def test_move_order_lands_in_the_battle_queue(
        self, executor, battle, deployed_squad, context
    ):
        result = await executor.execute(
            tool_call(
                "order_squad_move",
                squad_id=deployed_squad,
                target_x=3,
                target_y=2,
                pace=TacticalMovementPace.CHARGE.value,
            ),
            context(battle_state=battle),
        )

        assert result.success is True
        assert len(battle.pending_orders) == 1
        order = battle.pending_orders[0]
        assert order.squad_id == deployed_squad
        assert order.target_cell == CellCoordinates(x=3, y=2)
        assert order.pace == TACTICAL_PACE_SPEEDS[TacticalMovementPace.CHARGE]

    async def test_hold_order_keeps_the_squad_where_it_stands(
        self, executor, battle, deployed_squad, context
    ):
        result = await executor.execute(
            tool_call("order_squad_hold", squad_id=deployed_squad),
            context(battle_state=battle),
        )

        assert result.success is True
        order = battle.pending_orders[0]
        assert order.target_cell == CellCoordinates(x=1, y=1)
        assert order.pace == SPEED_DEFENSE_PACE

    async def test_reaction_order_carries_the_chosen_answer(
        self, executor, battle, deployed_squad, context
    ):
        result = await executor.execute(
            tool_call(
                "order_squad_reaction",
                squad_id=deployed_squad,
                reaction=ReactionType.FLEE.value,
            ),
            context(battle_state=battle),
        )

        assert result.success is True
        assert battle.pending_orders[0].reaction == ReactionType.FLEE

    async def test_order_to_a_squad_outside_the_battle_is_refused(
        self, executor, battle, context
    ):
        result = await executor.execute(
            tool_call("order_squad_hold", squad_id="sq_never_deployed"),
            context(battle_state=battle),
        )

        assert result.success is False
        assert battle.pending_orders == []

    async def test_battle_order_without_a_battle_is_refused(self, executor, context):
        """Приказ отряду вне боя - признак того, что сцена собрана неверно."""
        result = await executor.execute(
            tool_call("order_squad_hold", squad_id="sq_guards"), context()
        )

        assert result.success is False
        assert "battle_state" in result.error


# ==================================================================
# ОБЩИЕ НАВЫКИ
# ==================================================================


class TestGeneralHandlers:
    async def test_reply_returns_the_words_of_the_character(self, executor, context):
        result = await executor.execute(
            tool_call("reply", text="Мы подумаем над твоим предложением."), context()
        )

        assert result.success is True
        assert result.output == "Мы подумаем над твоим предложением."

    async def test_silence_is_a_legitimate_move(self, executor, context):
        """Без навыка молчания роль выдумывает действия ради самого действия."""
        result = await executor.execute(
            tool_call("stay_silent", reason="докладывать не о чем"), context()
        )

        assert result.success is True
        assert "докладывать не о чем" in result.output

    async def test_silence_needs_no_reason(self, executor, context):
        result = await executor.execute(tool_call("stay_silent"), context())

        assert result.success is True
        assert result.output
