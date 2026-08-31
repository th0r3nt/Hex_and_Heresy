"""
Обработчики навыков советника державы.
"""

from typing import Any

from src.back.l01_domain.factions.models.advisor import (
    AdvisorOption,
    AdvisorOptionKind,
    AdvisorProposal,
)
from src.back.l01_domain.llm.tools.definitions.advisor import PROPOSE_ADVISOR_ACTION
from src.back.l01_domain.llm.tools.schemas.advisor import ProposeAdvisorActionParams
from src.back.l02_services.mechanics.advisor.facade import AdvisorFacade
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.utils.event.registry import GameEvents


class AdvisorToolHandlers:
    """
    Инициатива советника: окно предложения с кнопками выбора для правителя.
    """

    def __init__(self, advisor_facade: AdvisorFacade) -> None:
        self._advisor = advisor_facade

    def register(self, executor: ToolExecutor) -> None:
        """
        Подключает навыки советника к исполнителю.
        """
        executor.register_handler(PROPOSE_ADVISOR_ACTION, self.propose_advisor_action)

    # ====================================================
    # Навыки
    # ====================================================

    async def propose_advisor_action(
        self, params: ProposeAdvisorActionParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Открывает правителю окно предложения и кладет его в реестр фасада.
        """
        faction_id = ctx.require_caller_faction_id("propose_advisor_action")

        options = [
            AdvisorOption(label=opt, kind=AdvisorOptionKind.ACCEPT) for opt in params.options
        ]
        if not any(o.kind == AdvisorOptionKind.DECLINE for o in options):
            options.append(AdvisorOption(label="Отклонить", kind=AdvisorOptionKind.DECLINE))

        proposal = AdvisorProposal(
            faction_id=faction_id,
            tick=ctx.world_state.time.total_ticks,
            title=params.title,
            message=params.message,
            options=options,
        )

        self._advisor._proposals[proposal.id] = proposal

        if self._advisor._event_bus is not None:
            await self._advisor._event_bus.publish(
                GameEvents.Advisor.PROPOSAL_OFFERED,
                faction_id=faction_id,
                proposal_id=proposal.id,
                title=proposal.title,
                message=proposal.message,
            )

        return (
            f"Сформировано предложение советника: «{proposal.title}».",
            {"proposal_id": proposal.id, "title": proposal.title},
        )
