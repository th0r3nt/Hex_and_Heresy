"""
Главный фасад подсистемы советника.
Единая точка входа для интерфейса: плановое предложение, свободный диалог
и реакция на выбор игрока.
"""

from typing import Optional

from src.back.l01_domain.exceptions.advisor import (
    AdvisorDisabledError,
    AdvisorProposalNotFoundError,
)
from src.back.l01_domain.exceptions.factions import FactionNotFoundError
from src.back.l01_domain.factions.models.advisor import (
    AdvisorAction,
    AdvisorActionOutcome,
    AdvisorActionStatus,
    AdvisorAnswer,
    AdvisorDecision,
    AdvisorProposal,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.llm import (
    ContextBuilderProtocol,
    LLMClientProtocol,
    PromptBuilderProtocol,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.advisor.generation import AdvisorGenerator
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.utils.event.registry import GameEvents

DEFAULT_TICKS_BETWEEN_PROPOSALS = 3


class AdvisorFacade:
    """
    Оркестрирует советника: когда ему говорить, что он говорит и что из его
    предложений доезжает до мира.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        prompt_builder: PromptBuilderProtocol,
        context_builder: ContextBuilderProtocol,
        tool_executor: Optional[ToolExecutor] = None,
        event_bus: Optional[EventBusProtocol] = None,
        is_enabled: bool = True,
        proposal_interval: int = DEFAULT_TICKS_BETWEEN_PROPOSALS,
    ) -> None:
        self._generator = AdvisorGenerator(
            llm_client=llm_client,
            prompt_builder=prompt_builder,
            context_builder=context_builder,
        )
        self._tool_executor = tool_executor
        self._event_bus = event_bus
        self._is_enabled = is_enabled
        self._proposal_interval = proposal_interval

        self._personalities: dict[str, str] = {}
        self._proposals: dict[str, AdvisorProposal] = {}
        self._last_proposal_ticks: dict[str, int] = {}

    def set_tool_executor(self, executor: ToolExecutor) -> None:
        """
        Устанавливает исполнитель инструментов при позднем связывании.
        """
        self._tool_executor = executor

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    def set_enabled(self, enabled: bool) -> None:
        self._is_enabled = enabled

    def set_personality(self, faction_id: str, personality_prompt: str) -> None:
        self._personalities[faction_id] = personality_prompt

    # ==================================================================
    # Пассивная инициатива
    # ==================================================================

    def should_offer(self, world_state: WorldState, faction_id: str) -> bool:
        last_tick = self._last_proposal_ticks.get(faction_id, 0)
        return (world_state.time.total_ticks - last_tick) >= self._proposal_interval

    async def offer_proposal(
        self,
        world_state: WorldState,
        faction_id: str,
        force: bool = False,
    ) -> Optional[AdvisorProposal]:
        if not self._is_enabled:
            return None

        faction = self._require_faction(world_state, faction_id)

        if not force and not self.should_offer(world_state, faction_id):
            return None

        self._last_proposal_ticks[faction_id] = world_state.time.total_ticks

        proposal = await self._generator.generate_proposal(
            world_state=world_state,
            faction=faction,
            personality_prompt=self._personalities.get(faction_id, ""),
        )
        if proposal is None:
            return None

        self._proposals[proposal.id] = proposal

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Advisor.PROPOSAL_OFFERED,
                faction_id=faction_id,
                proposal_id=proposal.id,
                title=proposal.title,
                message=proposal.message,
            )

        return proposal

    def pending_proposals(self, faction_id: str) -> list[AdvisorProposal]:
        return [
            proposal
            for proposal in self._proposals.values()
            if proposal.faction_id == faction_id and not proposal.is_answered
        ]

    def get_proposal(self, proposal_id: str) -> AdvisorProposal:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise AdvisorProposalNotFoundError(proposal_id)
        return proposal

    def forget_proposals(self) -> None:
        self._proposals.clear()
        self._last_proposal_ticks.clear()

    # ==================================================================
    # Диалоговый режим
    # ==================================================================

    async def ask(
        self,
        world_state: WorldState,
        faction_id: str,
        question: str,
    ) -> AdvisorAnswer:
        self._require_enabled()
        faction = self._require_faction(world_state, faction_id)

        return await self._generator.answer_question(
            world_state=world_state,
            faction=faction,
            question=question,
            personality_prompt=self._personalities.get(faction_id, ""),
        )

    # ==================================================================
    # Реакция на выбор игрока
    # ==================================================================

    async def answer_proposal(
        self,
        world_state: WorldState,
        proposal_id: str,
        option_id: str,
        player_reply: str = "",
    ) -> AdvisorDecision:
        self._require_enabled()

        proposal = self.get_proposal(proposal_id)
        faction = self._require_faction(world_state, proposal.faction_id)
        option = proposal.choose(option_id)

        await self._publish_answered(proposal, option.id, option.label)

        if option.is_refusal:
            return AdvisorDecision(proposal_id=proposal.id, option_id=option.id)

        reply, tool_calls = await self._generator.request_actions(
            world_state=world_state,
            faction=faction,
            proposal=proposal,
            option=option,
            player_reply=player_reply,
            personality_prompt=self._personalities.get(faction.id, ""),
        )

        outcomes: list[AdvisorActionOutcome] = []
        if self._tool_executor is not None and tool_calls:
            ctx = ToolExecutionContext(
                world_state=world_state,
                caller_faction_id=faction.id,
            )
            results = await self._tool_executor.execute_many(tool_calls, ctx)
            for res in results:
                status = (
                    AdvisorActionStatus.EXECUTED if res.success else AdvisorActionStatus.FAILED
                )
                outcomes.append(
                    AdvisorActionOutcome(
                        action=AdvisorAction(tool_name=res.tool_name),
                        status=status,
                        detail=res.output if res.success else (res.error or "ошибка"),
                    )
                )
                if res.success:
                    await self._publish_executed(faction.id, res.tool_name, res.output)

        return AdvisorDecision(
            proposal_id=proposal.id,
            option_id=option.id,
            advisor_reply=reply,
            outcomes=outcomes,
        )

    # ==================================================================
    # Служебное
    # ==================================================================

    def _require_enabled(self) -> None:
        if not self._is_enabled:
            raise AdvisorDisabledError()

    def _require_faction(self, world_state: WorldState, faction_id: str) -> Faction:
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise FactionNotFoundError(faction_id)
        return faction

    async def _publish_answered(
        self, proposal: AdvisorProposal, option_id: str, option_label: str
    ) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            GameEvents.Advisor.PROPOSAL_ANSWERED,
            faction_id=proposal.faction_id,
            proposal_id=proposal.id,
            option_id=option_id,
            option_label=option_label,
        )

    async def _publish_executed(self, faction_id: str, tool_name: str, detail: str) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            GameEvents.Advisor.ACTION_EXECUTED,
            faction_id=faction_id,
            tool_name=tool_name,
            detail=detail,
        )
