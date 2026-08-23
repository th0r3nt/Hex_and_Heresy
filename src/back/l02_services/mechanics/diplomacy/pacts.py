"""
Исполнение действующих пактов на каждом такте: переливы ресурсов по
торговым договорам, выплата дани вассалом и истечение сроков.

Домен (l01) хранит условия договоров, но не умеет ходить по времени -
отсчет сроков и движение казны это работа сервиса.
"""

from typing import Optional

from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.diplomacy.relation import DiplomaticRelation
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.event.registry import GameEvents


class PactUpkeepService:
    """
    Прогоняет все действующие соглашения мира через один такт.
    """

    def __init__(self, event_bus: Optional[EventBusProtocol] = None) -> None:
        self._event_bus = event_bus

    async def process_tick(self, world_state: WorldState) -> list[str]:
        """
        Исполняет обязательства сторон и снимает отработавшие пакты.
        Возвращает список закрытых пактов в виде 'faction_a:faction_b:тип'.
        """
        closed: list[str] = []

        for relation in world_state.diplomatic_relations:
            faction_a = world_state.get_faction(relation.faction_a_id)
            faction_b = world_state.get_faction(relation.faction_b_id)
            if faction_a is None or faction_b is None:
                continue

            await self._process_trade(relation, faction_a, faction_b, closed)
            await self._process_vassalage(relation, world_state, closed)
            await self._process_timed_pacts(relation, closed)

        return closed

    # ==================================================================
    # ОТДЕЛЬНЫЕ ТИПЫ ПАКТОВ
    # ==================================================================

    async def _process_trade(
        self,
        relation: DiplomaticRelation,
        faction_a: Faction,
        faction_b: Faction,
        closed: list[str],
    ) -> None:
        """
        Пассивный обмен ресурсами. Если одна из сторон не может исполнить
        свою часть, договор разрывается.
        """
        trade = relation.trade_agreement
        if trade is None:
            return

        a_can_pay = faction_a.can_afford(trade.give_resource, trade.give_amount)
        b_can_pay = faction_b.can_afford(trade.get_resource, trade.get_amount)

        if not (a_can_pay and b_can_pay):
            relation.trade_agreement = None
            await self._close(relation, "trade_agreement", closed, broken=True)
            return

        self._transfer(faction_a, faction_b, trade.give_resource, trade.give_amount)
        self._transfer(faction_b, faction_a, trade.get_resource, trade.get_amount)

        trade.remaining_turns -= 1
        if trade.remaining_turns <= 0:
            relation.trade_agreement = None
            await self._close(relation, "trade_agreement", closed)

    async def _process_vassalage(
        self, relation: DiplomaticRelation, world_state: WorldState, closed: list[str]
    ) -> None:
        """
        Вассал платит сюзерену дань. Неуплата означает разрыв вассалитета.
        """

        pact = relation.vassal_pact
        if pact is None:
            return

        vassal = world_state.get_faction(pact.vassal_faction_id)
        overlord = world_state.get_faction(pact.overlord_faction_id)
        if vassal is None or overlord is None:
            return

        if not vassal.can_afford(ResourceType.GOLD, pact.tribute_gold_per_turn):
            relation.vassal_pact = None
            await self._close(relation, "vassal_pact", closed, broken=True)
            return

        self._transfer(vassal, overlord, ResourceType.GOLD, pact.tribute_gold_per_turn)

        if self._event_bus is not None and pact.tribute_gold_per_turn > 0:
            await self._event_bus.publish(
                GameEvents.Diplomacy.TRIBUTE_PAID,
                payer_faction_id=vassal.id,
                receiver_faction_id=overlord.id,
                amount_gold=pact.tribute_gold_per_turn,
            )

    async def _process_timed_pacts(
        self, relation: DiplomaticRelation, closed: list[str]
    ) -> None:
        """
        Право прохода и военный союз просто доживают свой срок.
        """
        
        passage = relation.right_of_passage
        if passage is not None:
            passage.remaining_turns -= 1
            if passage.remaining_turns <= 0:
                relation.right_of_passage = None
                await self._close(relation, "right_of_passage", closed)

        alliance = relation.war_alliance
        if alliance is not None:
            alliance.remaining_turns -= 1
            if alliance.remaining_turns <= 0:
                relation.war_alliance = None
                await self._close(relation, "war_alliance", closed)

    # ==================================================================
    # ОБЩИЕ ХЕЛПЕРЫ
    # ==================================================================

    def _transfer(
        self, payer: Faction, receiver: Faction, resource: ResourceType, amount: float
    ) -> None:
        if amount <= 0:
            return
        payer.spend(resource, amount)
        receiver.earn(resource, amount)

    async def _close(
        self,
        relation: DiplomaticRelation,
        pact_name: str,
        closed: list[str],
        broken: bool = False,
    ) -> None:
        """
        Фиксирует закрытие пакта: по сроку или из-за неисполнения обязательств.
        """
        closed.append(f"{relation.faction_a_id}:{relation.faction_b_id}:{pact_name}")

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Diplomacy.PACT_BROKEN,
                faction_a_id=relation.faction_a_id,
                faction_b_id=relation.faction_b_id,
                pact_name=pact_name,
                reason="obligations_failed" if broken else "expired",
            )
