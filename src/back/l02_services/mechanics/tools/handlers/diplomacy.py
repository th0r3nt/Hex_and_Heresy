"""
Обработчики дипломатических навыков.

Здесь два разных типа хода, и путаться им нельзя:

* Решения лорда (объявить войну, продать проход, потребовать дань) ложатся
  на агрегат DiplomaticRelation. Инициатор такого решения - собеседник, тот,
  кто просил; отвечает и решает - сам лорд, от лица которого работает модель.
* Ходы своей державы (нанять гонца, снарядить посла, заплатить дань) уходят
  на DiplomacyFacade от лица фракции из обстановки.
"""

from typing import Optional

from src.back.l01_domain.exceptions.llm import ToolContextMissingError
from src.back.l01_domain.factions.models.diplomacy.pacts import (
    NonAggressionPact,
    RightOfPassagePact,
    TradeAgreement,
)
from src.back.l01_domain.llm.tools.diplomacy import (
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
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l02_services.mechanics.diplomacy.facade import DiplomacyFacade
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.utils.event.registry import GameEvents


def _require_counterpart(context: ToolExecutionContext, tool_name: str) -> str:
    """Собеседник, о судьбе договора с которым идет речь."""
    if not context.counterpart_faction_id:
        raise ToolContextMissingError(tool_name, "с кем именно идут переговоры")
    return context.counterpart_faction_id


def _require_ambassador(context: ToolExecutionContext, tool_name: str) -> str:
    """Посол, стоящий сейчас перед лордом."""
    if not context.ambassador_id:
        raise ToolContextMissingError(tool_name, "о каком после идет речь")
    return context.ambassador_id


def register_diplomacy_handlers(
    executor: ToolExecutor,
    diplomacy: DiplomacyFacade,
    event_bus: Optional[EventBusProtocol] = None,
) -> None:
    """
    Подключает дипломатические навыки к диспетчеру.
    """

    async def publish(event_name: str, **payload: object) -> None:
        if event_bus is not None:
            await event_bus.publish(event_name, **payload)

    # ==================================================================
    # РЕШЕНИЯ ЛОРДА
    # ==================================================================

    async def declare_war(
        context: ToolExecutionContext, params: DeclareWarParams
    ) -> str:
        counterpart = _require_counterpart(context, DECLARE_WAR.name)
        relation = context.world_state.get_or_create_relation(
            counterpart, context.faction_id
        )
        relation.declare_war()

        await publish(
            GameEvents.Diplomacy.WAR_DECLARED,
            faction_a_id=counterpart,
            faction_b_id=context.faction_id,
        )
        return f"Война державе '{counterpart}' объявлена."

    async def make_peace(
        context: ToolExecutionContext, params: MakePeaceParams
    ) -> str:
        counterpart = _require_counterpart(context, MAKE_PEACE.name)
        relation = context.world_state.get_or_create_relation(
            counterpart, context.faction_id
        )
        relation.make_peace()

        await publish(
            GameEvents.Diplomacy.PEACE_SIGNED,
            faction_a_id=counterpart,
            faction_b_id=context.faction_id,
        )
        return f"С державой '{counterpart}' заключен мир."

    async def propose_trade(
        context: ToolExecutionContext, params: ProposeTradeParams
    ) -> str:
        counterpart = _require_counterpart(context, PROPOSE_TRADE.name)
        relation = context.world_state.get_or_create_relation(
            counterpart, context.faction_id
        )
        relation.propose_trade(
            TradeAgreement(
                give_resource=params.give_resource,
                give_amount=params.give_amount,
                get_resource=params.get_resource,
                get_amount=params.get_amount,
                duration_turns=params.duration_turns,
                remaining_turns=params.duration_turns,
            )
        )

        await publish(
            GameEvents.Diplomacy.TRADE_AGREED,
            faction_a_id=counterpart,
            faction_b_id=context.faction_id,
        )
        return (
            f"Торговый договор с '{counterpart}' заключен на "
            f"{params.duration_turns} тактов."
        )

    async def establish_borders(
        context: ToolExecutionContext, params: EstablishBordersParams
    ) -> str:
        counterpart = _require_counterpart(context, ESTABLISH_BORDERS.name)
        relation = context.world_state.get_or_create_relation(
            counterpart, context.faction_id
        )
        relation.establish_borders(
            NonAggressionPact(allowed_hex_ids=params.allowed_hex_ids)
        )

        await publish(
            GameEvents.Diplomacy.PACT_FORMED,
            faction_a_id=counterpart,
            faction_b_id=context.faction_id,
            pact_name="non_aggression",
        )
        return (
            f"С державой '{counterpart}' установлены границы: "
            f"{len(params.allowed_hex_ids)} гексов под договором."
        )

    async def establish_right_of_passage(
        context: ToolExecutionContext, params: EstablishRightOfPassageParams
    ) -> str:
        counterpart = _require_counterpart(context, ESTABLISH_RIGHT_OF_PASSAGE.name)
        relation = context.world_state.get_or_create_relation(
            counterpart, context.faction_id
        )
        # Право прохода получает тот, кто просил, а не тот, кто согласился
        relation.establish_right_of_passage(
            RightOfPassagePact(
                beneficiary_faction_id=counterpart,
                allowed_hex_ids=params.allowed_hex_ids,
                toll_gold_per_crossing=params.toll_gold_per_crossing,
                duration_turns=params.duration_turns,
                remaining_turns=params.duration_turns,
            )
        )

        await publish(
            GameEvents.Diplomacy.PACT_FORMED,
            faction_a_id=counterpart,
            faction_b_id=context.faction_id,
            pact_name="right_of_passage",
        )
        return (
            f"Держава '{counterpart}' получила право прохода за "
            f"{params.toll_gold_per_crossing:.0f} золота с гекса."
        )

    async def demand_tribute(
        context: ToolExecutionContext, params: DemandTributeParams
    ) -> str:
        counterpart = _require_counterpart(context, DEMAND_TRIBUTE.name)
        relation = context.world_state.get_or_create_relation(
            counterpart, context.faction_id
        )
        relation.demand_tribute(params.gold_amount)

        await publish(
            GameEvents.Diplomacy.TRIBUTE_DEMANDED,
            demander_faction_id=context.faction_id,
            payer_faction_id=counterpart,
            amount_gold=params.gold_amount,
        )
        return (
            f"С державы '{counterpart}' затребована дань: "
            f"{params.gold_amount:.0f} золота."
        )

    async def execute_ambassador(
        context: ToolExecutionContext, params: ExecuteAmbassadorParams
    ) -> str:
        ambassador_id = _require_ambassador(context, EXECUTE_AMBASSADOR.name)
        ambassador = await diplomacy.execute_ambassador(
            world_state=context.world_state, ambassador_id=ambassador_id
        )
        return (
            f"Посол {ambassador.name} казнен. Державы отныне в состоянии войны."
        )

    # ==================================================================
    # ХОДЫ СВОЕЙ ДЕРЖАВЫ
    # ==================================================================

    async def send_dispatch(
        context: ToolExecutionContext, params: SendDispatchParams
    ) -> str:
        dispatch = await diplomacy.send_dispatch(
            world_state=context.world_state,
            sender_faction_id=context.faction_id,
            recipient_faction_id=params.recipient_faction_id,
            message_text=params.message_text,
        )
        return (
            f"Гонец с письмом к '{params.recipient_faction_id}' отправлен "
            f"(депеша {dispatch.id})."
        )

    async def send_ambassador(
        context: ToolExecutionContext, params: SendAmbassadorParams
    ) -> str:
        ambassador = await diplomacy.send_ambassador(
            world_state=context.world_state,
            faction_id=context.faction_id,
            name=params.name,
            target_faction_id=params.target_faction_id,
            traits=params.traits,
            escort_army_id=params.escort_army_id,
            negotiation_mode=params.negotiation_mode,
            directive=params.directive,
        )
        return (
            f"Посол {ambassador.name} выступил к державе "
            f"'{params.target_faction_id}'."
        )

    async def recall_ambassador(
        context: ToolExecutionContext, params: RecallAmbassadorParams
    ) -> str:
        ambassador = await diplomacy.recall_ambassador(
            world_state=context.world_state, ambassador_id=params.ambassador_id
        )
        return f"Посол {ambassador.name} отозван домой."

    async def pay_tribute(
        context: ToolExecutionContext, params: PayTributeParams
    ) -> str:
        amount = await diplomacy.pay_tribute(
            world_state=context.world_state,
            payer_faction_id=context.faction_id,
            receiver_faction_id=params.receiver_faction_id,
        )
        if amount <= 0:
            return f"Держава '{params.receiver_faction_id}' дани не требовала."
        return f"Дань выплачена: {amount:.0f} золота."

    executor.register(DECLARE_WAR, declare_war)
    executor.register(MAKE_PEACE, make_peace)
    executor.register(PROPOSE_TRADE, propose_trade)
    executor.register(ESTABLISH_BORDERS, establish_borders)
    executor.register(ESTABLISH_RIGHT_OF_PASSAGE, establish_right_of_passage)
    executor.register(DEMAND_TRIBUTE, demand_tribute)
    executor.register(EXECUTE_AMBASSADOR, execute_ambassador)

    executor.register(SEND_DISPATCH, send_dispatch)
    executor.register(SEND_AMBASSADOR, send_ambassador)
    executor.register(RECALL_AMBASSADOR, recall_ambassador)
    executor.register(PAY_TRIBUTE, pay_tribute)


__all__ = ["register_diplomacy_handlers"]
