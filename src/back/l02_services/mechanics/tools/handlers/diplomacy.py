"""
Обработчики навыков дипломатических переговоров и соглашений.
"""

from typing import Any

from src.back.l01_domain.factions.models.diplomacy.pacts import (
    NonAggressionPact,
    RightOfPassagePact,
    TradeAgreement,
)
from src.back.l01_domain.llm.tools.definitions.diplomacy import (
    DECLARE_WAR,
    DEMAND_TRIBUTE,
    ESTABLISH_BORDERS,
    ESTABLISH_RIGHT_OF_PASSAGE,
    EXECUTE_AMBASSADOR,
    MAKE_PEACE,
    PAY_TRIBUTE,
    PROPOSE_TRADE,
    RECALL_AMBASSADOR,
    SEND_AMBASSADOR,
    SEND_DISPATCH,
)
from src.back.l01_domain.llm.tools.schemas.diplomacy import (
    DeclareWarParams,
    DemandTributeParams,
    EstablishBordersParams,
    EstablishRightOfPassageParams,
    ExecuteAmbassadorParams,
    MakePeaceParams,
    PayTributeParams,
    ProposeTradeParams,
    RecallAmbassadorParams,
    SendAmbassadorParams,
    SendDispatchParams,
)
from src.back.l02_services.mechanics.diplomacy.facade import DiplomacyFacade
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.utils.event.registry import GameEvents


class DiplomacyToolHandlers:
    """
    Решения лорда в тронном зале и внешняя политика державы.

    Вызывающая сторона - всегда тот, кто говорит (`caller_faction_id`), а его
    собеседник приезжает в контексте целевой фракцией: от этой пары зависит,
    кто кому объявляет войну и кто через чьи земли пойдет.
    """

    def __init__(self, diplomacy_facade: DiplomacyFacade) -> None:
        self._diplomacy = diplomacy_facade

    def register(self, executor: ToolExecutor) -> None:
        """
        Подключает дипломатические навыки к исполнителю.
        """
        executor.register_handler(DECLARE_WAR, self.declare_war)
        executor.register_handler(MAKE_PEACE, self.make_peace)
        executor.register_handler(PROPOSE_TRADE, self.propose_trade)
        executor.register_handler(ESTABLISH_BORDERS, self.establish_borders)
        executor.register_handler(
            ESTABLISH_RIGHT_OF_PASSAGE, self.establish_right_of_passage
        )
        executor.register_handler(DEMAND_TRIBUTE, self.demand_tribute)
        executor.register_handler(SEND_DISPATCH, self.send_dispatch)
        executor.register_handler(SEND_AMBASSADOR, self.send_ambassador)
        executor.register_handler(RECALL_AMBASSADOR, self.recall_ambassador)
        executor.register_handler(EXECUTE_AMBASSADOR, self.execute_ambassador)
        executor.register_handler(PAY_TRIBUTE, self.pay_tribute)

    # ====================================================
    # Война и мир
    # ====================================================

    async def declare_war(
        self, params: DeclareWarParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Переводит отношения с собеседником в состояние войны.
        """
        caller_id = ctx.require_caller_faction_id("declare_war")
        target_id = ctx.require_target_faction_id("declare_war")

        relation = ctx.world_state.get_or_create_relation(caller_id, target_id)
        relation.declare_war()

        await self._publish(
            GameEvents.Diplomacy.WAR_DECLARED,
            faction_a_id=caller_id,
            faction_b_id=target_id,
            reason=params.reason or "объявление войны через дипломатию",
        )

        reason_text = f" по причине: {params.reason}" if params.reason else ""
        return (
            f"Фракция '{caller_id}' объявила войну фракции '{target_id}'{reason_text}.",
            {"faction_a_id": caller_id, "faction_b_id": target_id},
        )

    async def make_peace(
        self, params: MakePeaceParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Заключает мир с собеседником.
        """
        caller_id = ctx.require_caller_faction_id("make_peace")
        target_id = ctx.require_target_faction_id("make_peace")

        relation = ctx.world_state.get_or_create_relation(caller_id, target_id)
        relation.make_peace()

        await self._publish(
            GameEvents.Diplomacy.PEACE_SIGNED,
            faction_a_id=caller_id,
            faction_b_id=target_id,
        )

        terms_text = f" Условия: {params.terms_summary}" if params.terms_summary else ""
        return (
            f"Между фракциями '{caller_id}' и '{target_id}' заключен мир.{terms_text}",
            {"faction_a_id": caller_id, "faction_b_id": target_id},
        )

    # ====================================================
    # Пакты и соглашения
    # ====================================================

    async def propose_trade(
        self, params: ProposeTradeParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Заключает торговое соглашение об обмене ресурсами.
        """
        caller_id = ctx.require_caller_faction_id("propose_trade")
        target_id = ctx.require_target_faction_id("propose_trade")

        relation = ctx.world_state.get_or_create_relation(caller_id, target_id)
        agreement = TradeAgreement(
            give_resource=params.give_resource,
            give_amount=params.give_amount,
            get_resource=params.get_resource,
            get_amount=params.get_amount,
            duration_turns=params.duration_turns,
            remaining_turns=params.duration_turns,
        )
        relation.propose_trade(agreement)

        await self._publish(
            GameEvents.Diplomacy.TRADE_AGREED,
            faction_a_id=caller_id,
            faction_b_id=target_id,
        )

        return (
            f"Заключено торговое соглашение между '{caller_id}' и '{target_id}' на {params.duration_turns} тактов: "
            f"обмен {params.give_amount} {params.give_resource.value} на {params.get_amount} {params.get_resource.value}.",
            {"duration_turns": params.duration_turns},
        )

    async def establish_borders(
        self, params: EstablishBordersParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Заключает пакт о ненападении и разграничении территорий.
        """
        caller_id = ctx.require_caller_faction_id("establish_borders")
        target_id = ctx.require_target_faction_id("establish_borders")

        relation = ctx.world_state.get_or_create_relation(caller_id, target_id)
        relation.establish_borders(NonAggressionPact(allowed_hex_ids=params.allowed_hex_ids))

        await self._publish(
            GameEvents.Diplomacy.PACT_FORMED,
            faction_a_id=caller_id,
            faction_b_id=target_id,
            pact_name="non_aggression",
        )

        return (
            f"Заключен пакт о ненападении и разграничении территорий между '{caller_id}' и '{target_id}'.",
            {"allowed_hexes_count": len(params.allowed_hex_ids)},
        )

    async def establish_right_of_passage(
        self, params: EstablishRightOfPassageParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Пропускает армии собеседника через свои земли за плату.
        """
        caller_id = ctx.require_caller_faction_id("establish_right_of_passage")
        target_id = ctx.require_target_faction_id("establish_right_of_passage")

        # Право прохода дает хозяин земель гостю, а не себе: навык зовет тот,
        # через чьи владения пойдут чужие армии (см. game_mechanics/diplomacy.md).
        relation = ctx.world_state.get_or_create_relation(caller_id, target_id)
        relation.establish_right_of_passage(
            RightOfPassagePact(
                beneficiary_faction_id=target_id,
                allowed_hex_ids=params.allowed_hex_ids,
                toll_gold_per_crossing=params.toll_gold_per_crossing,
                duration_turns=params.duration_turns,
                remaining_turns=params.duration_turns,
            )
        )

        await self._publish(
            GameEvents.Diplomacy.PACT_FORMED,
            faction_a_id=caller_id,
            faction_b_id=target_id,
            pact_name="right_of_passage",
        )

        return (
            f"Фракция '{target_id}' получила право прохода через земли '{caller_id}' на {params.duration_turns} тактов.",
            {
                "duration_turns": params.duration_turns,
                "toll_gold": params.toll_gold_per_crossing,
            },
        )

    async def demand_tribute(
        self, params: DemandTributeParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Выставляет собеседнику требование дани.
        """
        caller_id = ctx.require_caller_faction_id("demand_tribute")
        target_id = ctx.require_target_faction_id("demand_tribute")

        relation = ctx.world_state.get_or_create_relation(target_id, caller_id)
        relation.demand_tribute(params.gold_amount)

        await self._publish(
            GameEvents.Diplomacy.TRIBUTE_DEMANDED,
            demander_faction_id=caller_id,
            payer_faction_id=target_id,
            amount_gold=params.gold_amount,
        )

        return (
            f"Фракция '{caller_id}' выставила требование дани фракции '{target_id}' на сумму {params.gold_amount:.1f} золота.",
            {"amount_gold": params.gold_amount},
        )

    # ====================================================
    # Логистика: гонцы и послы
    # ====================================================

    async def send_dispatch(
        self, params: SendDispatchParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Нанимает гонца и отправляет письмо чужому лорду.
        """
        caller_id = ctx.require_caller_faction_id("send_dispatch")
        dispatch = await self._diplomacy.send_dispatch(
            world_state=ctx.world_state,
            sender_faction_id=caller_id,
            recipient_faction_id=params.recipient_faction_id,
            message_text=params.message_text,
        )
        return (
            f"Письмо-депеша отправлено фракции '{params.recipient_faction_id}' "
            f"(время в пути: {dispatch.total_travel_ticks} тактов).",
            {"dispatch_id": dispatch.id, "cost_gold": dispatch.cost_gold},
        )

    async def send_ambassador(
        self, params: SendAmbassadorParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Снаряжает посла в чужую цитадель.
        """
        caller_id = ctx.require_caller_faction_id("send_ambassador")
        ambassador = await self._diplomacy.send_ambassador(
            world_state=ctx.world_state,
            faction_id=caller_id,
            name=params.name,
            target_faction_id=params.target_faction_id,
            traits=params.traits,
            escort_army_id=params.escort_army_id,
            negotiation_mode=params.negotiation_mode,
            directive=params.directive,
        )
        return (
            f"Посол {ambassador.name} отправлен в цитадель фракции '{params.target_faction_id}'.",
            {"ambassador_id": ambassador.id},
        )

    async def recall_ambassador(
        self, params: RecallAmbassadorParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Отзывает своего посла домой.
        """
        ambassador = await self._diplomacy.recall_ambassador(
            world_state=ctx.world_state,
            ambassador_id=params.ambassador_id,
        )
        return (
            f"Посол {ambassador.name} отозван с аудиенции домой.",
            {"ambassador_id": ambassador.id},
        )

    async def execute_ambassador(
        self, params: ExecuteAmbassadorParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Казнит посла собеседника: державы автоматически уходят в войну.

        Казнят того посла, который стоит на этой самой аудиенции, - он и
        приезжает в контексте актором.
        """
        ambassador_id = ctx.require_actor_id("execute_ambassador")
        ambassador = await self._diplomacy.execute_ambassador(
            world_state=ctx.world_state,
            ambassador_id=ambassador_id,
        )
        reason_text = f" по причине: {params.reason}" if params.reason else ""
        return (
            f"Посол {ambassador.name} казнен в тронном зале{reason_text}. Объявлена война!",
            {"ambassador_id": ambassador.id},
        )

    async def pay_tribute(
        self, params: PayTributeParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Выплачивает выставленную державе дань.
        """
        caller_id = ctx.require_caller_faction_id("pay_tribute")
        paid_amount = await self._diplomacy.pay_tribute(
            world_state=ctx.world_state,
            payer_faction_id=caller_id,
            receiver_faction_id=params.receiver_faction_id,
        )
        return (
            f"Выплачена дань в размере {paid_amount:.1f} золота фракции '{params.receiver_faction_id}'.",
            {"amount_gold": paid_amount},
        )

    # ====================================================
    # Служебное
    # ====================================================

    async def _publish(self, event_name: str, **payload: Any) -> None:
        """
        Публикует событие в шину дипломатии, если она вообще собрана.
        """
        if self._diplomacy._event_bus is None:
            return
        await self._diplomacy._event_bus.publish(event_name, **payload)
