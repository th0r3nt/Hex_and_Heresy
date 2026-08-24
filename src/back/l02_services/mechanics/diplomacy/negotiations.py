"""
Логика переговоров с чужой фракцией.

Лорд отвечает на письма и реплики послов строго структурированным JSON:
художественный текст плюс необязательное дипломатическое действие. Действие -
это и есть Function Calling из diplomacy.md: сервис переносит его на методы
агрегата DiplomaticRelation, который стоит на страже доменных правил.

Сами схемы ответа живут в домене
(l01_domain.factions.models.diplomacy.negotiations).
"""

from typing import Optional

from src.back.utils.event.registry import GameEvents

from src.back.l01_domain.factions.constants import (
    MAX_AUTO_NEGOTIATION_ROUNDS,
    DiplomaticActionType,
)
from src.back.l01_domain.factions.models.diplomacy.messengers import (
    Ambassador,
    Dispatch,
)
from src.back.l01_domain.factions.models.diplomacy.negotiations import (
    DiplomaticAction,
    LLMDiplomaticResponse,
    NegotiationLine,
    NegotiationTranscript,
)
from src.back.l01_domain.factions.models.diplomacy.pacts import (
    NonAggressionPact,
    RightOfPassagePact,
    TradeAgreement,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l01_domain.world.models.state import WorldState

from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder
from src.back.l03_infrastructure.llm.prompt.catalog import PromptCatalog, get_faction_prompt_path

# ==================================================================
# СЕРВИС
# ==================================================================


class NegotiationService:
    """
    Ведет диалог с лордом чужой фракции и применяет принятые им решения.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        event_bus: Optional[EventBusProtocol] = None,
        prompt_builder: Optional[PromptBuilder] = None,
    ) -> None:
        self._llm = llm_client
        self._event_bus = event_bus
        self._prompt_builder = prompt_builder or PromptBuilder()

    async def answer_dispatch(
        self, world_state: WorldState, dispatch: Dispatch
    ) -> LLMDiplomaticResponse:
        """
        Лорд-получатель читает доставленное письмо и отвечает на него.
        """

        recipient = self._require_faction(world_state, dispatch.recipient_faction_id)
        sender = self._require_faction(world_state, dispatch.sender_faction_id)

        response = await self._llm.generate_structured(
            system_prompt=self._build_lord_prompt(world_state, recipient, sender),
            user_prompt=f"Письмо от фракции '{sender.name}':\n{dispatch.message_text}",
            response_model=LLMDiplomaticResponse,
            temperature=0.7,
        )

        await self.apply_action(world_state, sender.id, recipient.id, response.action)
        return response

    async def reply_to_player(
        self, world_state: WorldState, ambassador: Ambassador, player_text: str
    ) -> LLMDiplomaticResponse:
        """
        Ручной режим аудиенции: игрок говорит от лица своего посла,
        чужой лорд отвечает.
        """
        envoy_faction = self._require_faction(world_state, ambassador.faction_id)
        host_faction = self._require_faction(
            world_state, ambassador.target_faction_id or ""
        )

        sys_prompt = self._build_lord_prompt(world_state, host_faction, envoy_faction, ambassador)
        
        response = await self._llm.generate_structured(
            system_prompt=sys_prompt,
            user_prompt=f"Посол {ambassador.name} говорит:\n{player_text}",
            response_model=LLMDiplomaticResponse,
            temperature=0.8,
        )

        await self.apply_action(
            world_state, envoy_faction.id, host_faction.id, response.action
        )
        return response

    async def run_auto_negotiation(
        self,
        world_state: WorldState,
        ambassador: Ambassador,
        max_rounds: int = MAX_AUTO_NEGOTIATION_ROUNDS,
    ) -> NegotiationTranscript:
        """
        Автоматический режим: посол-LLM торгуется с лордом-LLM по директиве
        игрока, пока лорд не примет решение или не кончатся раунды.
        """
        envoy_faction = self._require_faction(world_state, ambassador.faction_id)
        host_faction = self._require_faction(
            world_state, ambassador.target_faction_id or ""
        )

        envoy_prompt = self._build_envoy_prompt(world_state, ambassador, envoy_faction, host_faction)
        lord_prompt = self._build_lord_prompt(
            world_state, host_faction, envoy_faction, ambassador
        )

        transcript = NegotiationTranscript()
        last_lord_words = "Лорд молча ждет первого слова посла."

        for _ in range(max_rounds):
            envoy_text = await self._llm.generate_text(
                system_prompt=envoy_prompt,
                user_prompt=f"Слова чужого лорда:\n{last_lord_words}",
                temperature=0.9,
            )
            transcript.lines.append(
                NegotiationLine(speaker="ambassador", text=envoy_text)
            )

            response = await self._llm.generate_structured(
                system_prompt=lord_prompt,
                user_prompt=f"Посол {ambassador.name} говорит:\n{envoy_text}",
                response_model=LLMDiplomaticResponse,
                temperature=0.8,
            )
            transcript.lines.append(
                NegotiationLine(speaker="lord", text=response.reply_text)
            )
            transcript.final_response = response

            if response.action is not None and response.action.kind != DiplomaticActionType.NONE:
                await self.apply_action(
                    world_state, envoy_faction.id, host_faction.id, response.action
                )
                break

            last_lord_words = response.reply_text

        return transcript

    # ==================================================================
    # ПРИМЕНЕНИЕ РЕШЕНИЙ ЛОРДА
    # ==================================================================

    async def apply_action(
        self,
        world_state: WorldState,
        initiator_faction_id: str,
        responder_faction_id: str,
        action: Optional[DiplomaticAction],
    ) -> bool:
        """
        Переносит решение лорда на агрегат отношений.
        Возвращает True, если состояние мира изменилось.

        Казнь посла здесь не исполняется: она требует работы с самим послом
        и остается за DiplomacyFacade.
        """
        if action is None or action.kind == DiplomaticActionType.NONE:
            return False

        relation = world_state.get_or_create_relation(
            initiator_faction_id, responder_faction_id
        )

        if action.kind == DiplomaticActionType.DECLARE_WAR:
            relation.declare_war()
            await self._publish(
                GameEvents.Diplomacy.WAR_DECLARED,
                initiator_faction_id,
                responder_faction_id,
            )
            return True

        if action.kind == DiplomaticActionType.MAKE_PEACE:
            relation.make_peace()
            await self._publish(
                GameEvents.Diplomacy.PEACE_SIGNED,
                initiator_faction_id,
                responder_faction_id,
            )
            return True

        if action.kind == DiplomaticActionType.PROPOSE_TRADE:
            if action.give_resource is None or action.get_resource is None:
                return False
            relation.propose_trade(
                TradeAgreement(
                    give_resource=action.give_resource,
                    give_amount=action.give_amount,
                    get_resource=action.get_resource,
                    get_amount=action.get_amount,
                    duration_turns=action.duration_turns,
                    remaining_turns=action.duration_turns,
                )
            )
            await self._publish(
                GameEvents.Diplomacy.TRADE_AGREED,
                initiator_faction_id,
                responder_faction_id,
            )
            return True

        if action.kind == DiplomaticActionType.ESTABLISH_BORDERS:
            relation.establish_borders(
                NonAggressionPact(allowed_hex_ids=action.allowed_hex_ids)
            )
            await self._publish(
                GameEvents.Diplomacy.PACT_FORMED,
                initiator_faction_id,
                responder_faction_id,
                pact_name="non_aggression",
            )
            return True

        if action.kind == DiplomaticActionType.ESTABLISH_RIGHT_OF_PASSAGE:
            relation.establish_right_of_passage(
                RightOfPassagePact(
                    beneficiary_faction_id=initiator_faction_id,
                    allowed_hex_ids=action.allowed_hex_ids,
                    toll_gold_per_crossing=action.gold_amount,
                    duration_turns=action.duration_turns,
                    remaining_turns=action.duration_turns,
                )
            )
            await self._publish(
                GameEvents.Diplomacy.PACT_FORMED,
                initiator_faction_id,
                responder_faction_id,
                pact_name="right_of_passage",
            )
            return True

        if action.kind == DiplomaticActionType.DEMAND_TRIBUTE:
            relation.demand_tribute(action.gold_amount)
            if self._event_bus is not None:
                await self._event_bus.publish(
                    GameEvents.Diplomacy.TRIBUTE_DEMANDED,
                    demander_faction_id=responder_faction_id,
                    payer_faction_id=initiator_faction_id,
                    amount_gold=action.gold_amount,
                )
            return True

        return False

    # ==================================================================
    # СБОРКА ПРОМПТОВ
    # ==================================================================

    def _build_lord_prompt(
        self,
        world_state: WorldState,
        lord_faction: Faction,
        counterpart_faction: Faction,
        ambassador: Optional[Ambassador] = None,
    ) -> str:
        # Собираем статический базис
        static_context = self._prompt_builder.build([
            PromptCatalog.BASE.PERSONA,
            PromptCatalog.BASE.MECHANICS.STRATEGIC,
            PromptCatalog.ROLES.LORD,
            get_faction_prompt_path(lord_faction.race),
            PromptCatalog.LORE.BASIC.MEDIUM
        ])

        lord = lord_faction.lord
        guest = ""
        if ambassador is not None:
            traits = ", ".join(ambassador.traits) if ambassador.traits else "неизвестны"
            guest = f" Перед тобой посол {ambassador.name} (черты: {traits})."

        dynamic_context = (
            f"Ты - {lord.display_name}, правитель фракции '{lord_faction.name}'.\n"
            f"Твой архетип: {lord.archetype.name}. {lord.archetype.description}\n"
            f"Твоя черта: {lord.trait.name}. {lord.trait.text_fragment}\n\n"
            f"С тобой ведет переговоры фракция '{counterpart_faction.name}'.{guest}\n\n"
            f"{self._render_relation_context(world_state, lord_faction, counterpart_faction)}"
        )

        return f"{static_context}\n\n{dynamic_context}"

    def _build_envoy_prompt(
        self,
        world_state: WorldState,
        ambassador: Ambassador,
        envoy_faction: Faction,
        host_faction: Faction,
    ) -> str:
        static_context = self._prompt_builder.build([
            PromptCatalog.BASE.PERSONA,
            PromptCatalog.BASE.MECHANICS.STRATEGIC,
            PromptCatalog.ROLES.DIPLOMAT,
            get_faction_prompt_path(envoy_faction.race)
        ])

        traits = ", ".join(ambassador.traits) if ambassador.traits else "обычные"
        directive = ambassador.directive or "Добиться мира на любых разумных условиях."

        dynamic_context = (
            f"Ты - {ambassador.name}, посол фракции '{envoy_faction.name}'. Твои черты: {traits}.\n"
            f"Ты стоишь в цитадели фракции '{host_faction.name}' перед ее правителем.\n\n"
            f"Директива твоего лорда: {directive}\n\n"
            f"{self._render_relation_context(world_state, envoy_faction, host_faction)}"
        )

        return f"{static_context}\n\n{dynamic_context}"

    def _render_relation_context(
        self, world_state: WorldState, faction: Faction, counterpart: Faction
    ) -> str:
        """
        Короткая сводка текущих отношений двух фракций для промпта.
        """
        relation = world_state.get_relation(faction.id, counterpart.id)
        if relation is None:
            return "Между вами нет ни договоров, ни объявленной войны."

        active_pacts = [
            name
            for name, pact in (
                ("торговое соглашение", relation.trade_agreement),
                ("договор о ненападении", relation.non_aggression_pact),
                ("право прохода", relation.right_of_passage),
                ("вассалитет", relation.vassal_pact),
                ("обмен разведданными", relation.intelligence_sharing),
                ("обмен заложниками", relation.hostage_exchange),
                ("военный союз", relation.war_alliance),
            )
            if pact is not None
        ]

        lines = [f"Текущее состояние отношений: {relation.stance.value}."]
        if active_pacts:
            lines.append("Действующие соглашения: " + ", ".join(active_pacts) + ".")
        if relation.tribute_demanded_gold:
            lines.append(f"Не закрыто требование дани: {relation.tribute_demanded_gold} золота.")

        return "\n".join(lines)

    # ==================================================================
    # ХЕЛПЕРЫ
    # ==================================================================

    async def _publish(
        self,
        event_name: str,
        faction_a_id: str,
        faction_b_id: str,
        **extra: object,
    ) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            event_name, faction_a_id=faction_a_id, faction_b_id=faction_b_id, **extra
        )

    def _require_faction(self, world_state: WorldState, faction_id: str) -> Faction:
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise ValueError(f"Фракция {faction_id} не найдена")
        return faction


__all__ = ["NegotiationService"]
