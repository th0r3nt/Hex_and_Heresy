"""
Главный фасад оркестрации ходов (стратегических и тактических).
"""

from typing import Optional

from src.back.l01_domain.factions.constants import WorkerRiskTier
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.orchestrator import (
    GlobalTurnReport,
    StrategicTurnOrchestrator,
)


class TurnsFacade:
    """
    Единая точка входа для исполнения ходов игры.
    Делегирует расчет специализированным оркестраторам.
    """

    def __init__(
        self,
        strategic_orchestrator: Optional[StrategicTurnOrchestrator] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._event_bus = event_bus
        self._strategic_orchestrator = strategic_orchestrator or StrategicTurnOrchestrator(
            event_bus=event_bus
        )

    async def execute_strategic_turn(
        self,
        world_state: WorldState,
        worker_assignments: Optional[dict[str, WorkerRiskTier]] = None,
    ) -> GlobalTurnReport:
        """
        Выполняет расчет глобального такта стратегической карты.
        """
        return await self._strategic_orchestrator.execute_turn(
            world_state=world_state, worker_assignments=worker_assignments
        )

    # TODO: написать логику тактических ходов