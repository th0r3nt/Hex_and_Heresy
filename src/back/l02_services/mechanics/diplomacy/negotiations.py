"""
Логика переговоров с чужой фракцией через вызовы инструментов (Function Calling).
"""

from typing import Optional

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
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.prompts import PromptCatalog, get_faction_prompt_key
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.llm import (
    ContextBuilderProtocol,
    LLMClientProtocol,
    PromptBuilderProtocol,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.l01_domain.llm.tools.catalog import Toolset, get_toolset


class NegotiationService:
    """
    Ведет диалог с лордом чужой фракции и применяет принятые им решения через ToolExecutor.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        prompt_builder: PromptBuilderProtocol,
        context_builder: ContextBuilderProtocol,
        tool_executor: Optional[ToolExecutor] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._llm = llm_client
        self._prompt_builder = prompt_builder
        self._context_builder = context_builder
        self._tool_executor = tool_executor
        self._event_bus = event_bus

    def set_tool_executor(self, executor: ToolExecutor) -> None:
        self._tool_executor = executor

    async def answer_dispatch(
        self, world_state: WorldState, dispatch: Dispatch
    ) -> LLMDiplomaticResponse:
        """
        Лорд-получатель читает доставленное письмо и отвечает на него через инструменты аудиенции.
        """
        recipient = self._require_faction(world_state, dispatch.recipient_faction_id)
        sender = self._require_faction(world_state, dispatch.sender_faction_id)

        system_prompt = self._build_lord_prompt(world_state, recipient, sender)
        user_prompt = f"Письмо от фракции '{sender.name}':\n{dispatch.message_text}"
        tools = get_toolset(Toolset.LORD_AUDIENCE)

        content, tool_calls = await self._llm.generate_with_tools(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tools,
            temperature=0.7,
        )

        reply_text = content.strip() or "Лорд ознакомился с депешей."
        action_kind = DiplomaticActionType.NONE

        if self._tool_executor is not None and tool_calls:
            ctx = ToolExecutionContext(
                world_state=world_state,
                caller_faction_id=recipient.id,
                target_faction_id=sender.id,
            )
            results = await self._tool_executor.execute_many(tool_calls, ctx)
            for res in results:
                if res.tool_name == "reply":
                    reply_text = res.output or reply_text
                elif res.success:
                    try:
                        action_kind = DiplomaticActionType(res.tool_name)
                    except ValueError:
                        pass

        return LLMDiplomaticResponse(
            reply_text=reply_text,
            action=(
                DiplomaticAction(kind=action_kind)
                if action_kind != DiplomaticActionType.NONE
                else None
            ),
        )

    async def reply_to_player(
        self, world_state: WorldState, ambassador: Ambassador, player_text: str
    ) -> LLMDiplomaticResponse:
        """
        Ручной режим аудиенции: игрок говорит от лица посла, чужой лорд отвечает.
        """
        envoy_faction = self._require_faction(world_state, ambassador.faction_id)
        host_faction = self._require_faction(world_state, ambassador.target_faction_id or "")

        sys_prompt = self._build_lord_prompt(
            world_state, host_faction, envoy_faction, ambassador
        )
        tools = get_toolset(Toolset.LORD_AUDIENCE)

        content, tool_calls = await self._llm.generate_with_tools(
            system_prompt=sys_prompt,
            user_prompt=f"Посол {ambassador.name} говорит:\n{player_text}",
            tools=tools,
            temperature=0.8,
        )

        reply_text = content.strip() or "Лорд молча слушает посла."
        action_kind = DiplomaticActionType.NONE

        if self._tool_executor is not None and tool_calls:
            ctx = ToolExecutionContext(
                world_state=world_state,
                caller_faction_id=host_faction.id,
                target_faction_id=envoy_faction.id,
                actor_id=ambassador.id,
            )
            results = await self._tool_executor.execute_many(tool_calls, ctx)
            for res in results:
                if res.tool_name == "reply":
                    reply_text = res.output or reply_text
                elif res.success:
                    try:
                        action_kind = DiplomaticActionType(res.tool_name)
                    except ValueError:
                        pass

        return LLMDiplomaticResponse(
            reply_text=reply_text,
            action=(
                DiplomaticAction(kind=action_kind)
                if action_kind != DiplomaticActionType.NONE
                else None
            ),
        )

    async def run_auto_negotiation(
        self,
        world_state: WorldState,
        ambassador: Ambassador,
        max_rounds: int = MAX_AUTO_NEGOTIATION_ROUNDS,
    ) -> NegotiationTranscript:
        """
        Автоматический режим: посол-LLM торгуется с лордом-LLM по директиве.
        """
        envoy_faction = self._require_faction(world_state, ambassador.faction_id)
        host_faction = self._require_faction(world_state, ambassador.target_faction_id or "")

        envoy_prompt = self._build_envoy_prompt(
            world_state, ambassador, envoy_faction, host_faction
        )
        lord_prompt = self._build_lord_prompt(
            world_state, host_faction, envoy_faction, ambassador
        )

        transcript = NegotiationTranscript()
        last_lord_words = "Лорд молча ждет первого слова посла."

        for _ in range(max_rounds):
            # 1. Реплика посла
            envoy_content, _ = await self._llm.generate_with_tools(
                system_prompt=envoy_prompt,
                user_prompt=f"Слова чужого лорда:\n{last_lord_words}",
                tools=get_toolset(Toolset.AMBASSADOR_MISSION),
                temperature=0.9,
            )
            envoy_text = envoy_content.strip() or "Посол излагает предложение своего лорда."
            transcript.lines.append(NegotiationLine(speaker="ambassador", text=envoy_text))

            # 2. Ответ лорда
            lord_content, tool_calls = await self._llm.generate_with_tools(
                system_prompt=lord_prompt,
                user_prompt=f"Посол {ambassador.name} говорит:\n{envoy_text}",
                tools=get_toolset(Toolset.LORD_AUDIENCE),
                temperature=0.8,
            )
            lord_reply = lord_content.strip() or "Лорд слушает предложение."
            transcript.lines.append(NegotiationLine(speaker="lord", text=lord_reply))

            action_kind = DiplomaticActionType.NONE
            if self._tool_executor is not None and tool_calls:
                ctx = ToolExecutionContext(
                    world_state=world_state,
                    caller_faction_id=host_faction.id,
                    target_faction_id=envoy_faction.id,
                    actor_id=ambassador.id,
                )
                results = await self._tool_executor.execute_many(tool_calls, ctx)
                for res in results:
                    if res.tool_name == "reply":
                        lord_reply = res.output or lord_reply
                    elif res.success:
                        try:
                            action_kind = DiplomaticActionType(res.tool_name)
                        except ValueError:
                            pass

            response = LLMDiplomaticResponse(
                reply_text=lord_reply,
                action=(
                    DiplomaticAction(kind=action_kind)
                    if action_kind != DiplomaticActionType.NONE
                    else None
                ),
            )
            transcript.final_response = response

            if action_kind != DiplomaticActionType.NONE:
                break

            last_lord_words = lord_reply

        return transcript

    # ==================================================================
    # Сборка промптов
    # ==================================================================

    def _build_lord_prompt(
        self,
        world_state: WorldState,
        lord_faction: Faction,
        counterpart_faction: Faction,
        ambassador: Optional[Ambassador] = None,
    ) -> str:
        static_context = self._prompt_builder.build(
            [
                PromptCatalog.BASE.PERSONA,
                PromptCatalog.BASE.MECHANICS.STRATEGIC,
                PromptCatalog.ROLES.LORD,
                get_faction_prompt_key(lord_faction.race),
                PromptCatalog.LORE.BASIC.MEDIUM,
            ]
        )
        blocks = self._context_builder.build_lord_context(
            world_state, lord_faction, counterpart_faction, ambassador
        )
        dynamic_context = self._context_builder.render(blocks)
        return f"{static_context}\n\n{dynamic_context}"

    def _build_envoy_prompt(
        self,
        world_state: WorldState,
        ambassador: Ambassador,
        envoy_faction: Faction,
        host_faction: Faction,
    ) -> str:
        static_context = self._prompt_builder.build(
            [
                PromptCatalog.BASE.PERSONA,
                PromptCatalog.BASE.MECHANICS.STRATEGIC,
                PromptCatalog.ROLES.DIPLOMAT,
                get_faction_prompt_key(envoy_faction.race),
            ]
        )
        blocks = self._context_builder.build_ambassador_context(
            world_state, ambassador, envoy_faction, host_faction
        )
        dynamic_context = self._context_builder.render(blocks)
        return f"{static_context}\n\n{dynamic_context}"

    def _require_faction(self, world_state: WorldState, faction_id: str) -> Faction:
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise ValueError(f"Фракция {faction_id} не найдена")
        return faction
