"""
Главный фасад дипломатии.
Единая точка входа для остальных модулей: отправка депеш и послов,
дипломатический шаг глобального такта и ведение переговоров.
"""

from random import Random
from typing import Optional

from src.back.l01_domain.exceptions import AmbassadorUnavailableError
from src.back.l01_domain.factions.constants import (
    AmbassadorStatus,
    NegotiationMode,
    ResourceType,
)
from src.back.l01_domain.factions.models.diplomacy.messengers import (
    Ambassador,
    Dispatch,
)
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l01_domain.world.models.reports import DiplomacyTickReport
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.diplomacy.ambassador import AmbassadorService
from src.back.l02_services.mechanics.diplomacy.messenger import DispatchService
from src.back.l02_services.mechanics.diplomacy.negotiations import (
    DiplomaticActionType,
    LLMDiplomaticResponse,
    NegotiationService,
    NegotiationTranscript,
)
from src.back.l02_services.mechanics.diplomacy.pacts import PactUpkeepService
from src.back.utils.event.registry import GameEvents


class DiplomacyFacade:
    """
    Оркестрирует гонцов, послов, пакты и переговоры.

    LLM нужен только для переговоров, поэтому клиент необязателен: стратегический
    такт (process_tick) считается и без него.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClientProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        rng: Optional[Random] = None,
    ) -> None:
        self._event_bus = event_bus
        self._dispatches = DispatchService(event_bus=event_bus, rng=rng)
        self._ambassadors = AmbassadorService(event_bus=event_bus)
        self._pacts = PactUpkeepService(event_bus=event_bus)
        self._negotiations = (
            NegotiationService(llm_client=llm_client, event_bus=event_bus)
            if llm_client is not None
            else None
        )

    # ==================================================================
    # ДЕЙСТВИЯ ИГРОКА
    # ==================================================================

    async def send_dispatch(
        self,
        world_state: WorldState,
        sender_faction_id: str,
        recipient_faction_id: str,
        message_text: str,
    ) -> Dispatch:
        """Нанимает гонца и отправляет письмо чужому лорду."""
        return await self._dispatches.send(
            world_state=world_state,
            sender_faction_id=sender_faction_id,
            recipient_faction_id=recipient_faction_id,
            message_text=message_text,
        )

    async def send_ambassador(
        self,
        world_state: WorldState,
        faction_id: str,
        name: str,
        target_faction_id: str,
        traits: Optional[list[str]] = None,
        escort_army_id: Optional[str] = None,
        negotiation_mode: NegotiationMode = NegotiationMode.AUTOMATIC,
        directive: Optional[str] = None,
    ) -> Ambassador:
        """Отправляет посла в чужую цитадель."""
        return await self._ambassadors.send(
            world_state=world_state,
            faction_id=faction_id,
            name=name,
            target_faction_id=target_faction_id,
            traits=traits,
            escort_army_id=escort_army_id,
            negotiation_mode=negotiation_mode,
            directive=directive,
        )

    async def pay_tribute(
        self, world_state: WorldState, payer_faction_id: str, receiver_faction_id: str
    ) -> float:
        """
        Закрывает выставленное требование дани. Возвращает выплаченную сумму.
        """
        relation = world_state.get_or_create_relation(
            payer_faction_id, receiver_faction_id
        )
        amount = relation.tribute_demanded_gold or 0.0
        if amount <= 0:
            return 0.0

        payer = world_state.get_faction(payer_faction_id)
        receiver = world_state.get_faction(receiver_faction_id)
        if payer is None or receiver is None:
            raise ValueError("Одна из фракций требования дани не найдена")

        payer.spend(ResourceType.GOLD, amount)
        receiver.earn(ResourceType.GOLD, amount)
        relation.settle_tribute()

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Diplomacy.TRIBUTE_PAID,
                payer_faction_id=payer_faction_id,
                receiver_faction_id=receiver_faction_id,
                amount_gold=amount,
            )

        return amount

    # ==================================================================
    # ГЛОБАЛЬНЫЙ ТАКТ
    # ==================================================================

    async def process_tick(self, world_state: WorldState) -> DiplomacyTickReport:
        """
        Дипломатический шаг такта: исполнение пактов, продвижение гонцов
        и послов по карте.
        """
        expired_pacts = await self._pacts.process_tick(world_state)
        delivered, intercepted = await self._dispatches.process_tick(world_state)
        arrived = await self._ambassadors.process_tick(world_state)

        return DiplomacyTickReport(
            delivered_dispatch_ids=[d.id for d in delivered],
            intercepted_dispatch_ids=[d.id for d in intercepted],
            arrived_ambassador_ids=[a.id for a in arrived],
            expired_pacts=expired_pacts,
        )

    # ==================================================================
    # ПЕРЕГОВОРЫ
    # ==================================================================

    async def answer_dispatch(
        self, world_state: WorldState, dispatch: Dispatch
    ) -> LLMDiplomaticResponse:
        """
        Лорд-получатель отвечает на доставленное письмо и, если решит,
        вызывает дипломатическую функцию.
        """
        return await self._require_negotiations().answer_dispatch(world_state, dispatch)

    async def speak_to_lord(
        self, world_state: WorldState, ambassador_id: str, player_text: str
    ) -> LLMDiplomaticResponse:
        """
        Ручной режим аудиенции: игрок говорит от лица посла.
        """
        negotiations = self._require_negotiations()
        ambassador = self._require_ambassador(world_state, ambassador_id)
        response = await negotiations.reply_to_player(
            world_state, ambassador, player_text
        )
        await self._resolve_ambassador_fate(world_state, ambassador, response)
        return response

    async def run_auto_negotiation(
        self, world_state: WorldState, ambassador_id: str
    ) -> NegotiationTranscript:
        """
        Автоматический режим: посол торгуется с чужим лордом по директиве.
        """
        negotiations = self._require_negotiations()
        ambassador = self._require_ambassador(world_state, ambassador_id)
        transcript = await negotiations.run_auto_negotiation(world_state, ambassador)
        if transcript.final_response is not None:
            await self._resolve_ambassador_fate(
                world_state, ambassador, transcript.final_response
            )
        return transcript

    async def execute_ambassador(
        self, world_state: WorldState, ambassador_id: str
    ) -> Ambassador:
        """Казнь посла чужим лордом: посол гибнет, фракции уходят в войну."""
        return await self._ambassadors.execute_ambassador(world_state, ambassador_id)

    async def recall_ambassador(
        self, world_state: WorldState, ambassador_id: str
    ) -> Ambassador:
        """Аудиенция окончена: посол уходит домой."""
        return await self._ambassadors.send_home(world_state, ambassador_id)

    # ==================================================================
    # ВНУТРЕННЯЯ ЛОГИКА
    # ==================================================================

    async def _resolve_ambassador_fate(
        self,
        world_state: WorldState,
        ambassador: Ambassador,
        response: LLMDiplomaticResponse,
    ) -> None:
        """
        Единственное решение лорда, которое сервис переговоров не исполняет
        сам, - казнь посла: она требует работы с картой и статусом посла.
        """
        if response.action is None:
            return
        if response.action.kind != DiplomaticActionType.EXECUTE_AMBASSADOR:
            return

        await self._ambassadors.execute_ambassador(world_state, ambassador.id)

    def _require_negotiations(self) -> NegotiationService:
        if self._negotiations is None:
            raise ValueError(
                "Переговоры недоступны: DiplomacyFacade собран без LLM-клиента"
            )
        return self._negotiations

    def _require_ambassador(
        self, world_state: WorldState, ambassador_id: str
    ) -> Ambassador:
        """
        Отдает посла, который уже стоит на аудиенции: в пути переговоры вести не с кем.
        """
        for ambassador in world_state.ambassadors:
            if ambassador.id != ambassador_id:
                continue
            if ambassador.status != AmbassadorStatus.IN_AUDIENCE:
                raise AmbassadorUnavailableError(ambassador_id, ambassador.status.value)
            return ambassador
        raise AmbassadorUnavailableError(ambassador_id, "not_found")
