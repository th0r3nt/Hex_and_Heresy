"""
Мастер-оркестратор стратегического хода (конвейерный пайплайн).
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import WorkerRiskTier
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.economy import (
    FactionEconomyReport,
    StrategicEconomyService,
)
from src.back.l02_services.turns.strategic.events import (
    EventsStepReport,
    StrategicEventsService,
)
from src.back.l02_services.turns.strategic.movement import (
    MovementStepReport,
    StrategicMovementService,
)


class GlobalTurnReport(BaseModel):
    """
    Итоговый структурированный отчет о расчете глобального хода.
    """

    events_report: EventsStepReport = Field(...)
    economy_reports: dict[str, FactionEconomyReport] = Field(default_factory=dict)
    movement_report: MovementStepReport = Field(...)


class StrategicTurnOrchestrator:
    """
    Главный оркестратор глобального хода.
    Строго последовательно выполняет конвейер:

    [1. События и время] -> [2. Экономика и содержание] -> [3. Передвижения и логистика] -> [4. Итоговый отчет].
    """

    def __init__(
        self,
        events_service: Optional[StrategicEventsService] = None,
        economy_service: Optional[StrategicEconomyService] = None,
        movement_service: Optional[StrategicMovementService] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._event_bus = event_bus
        self._events_service = events_service or StrategicEventsService(event_bus=event_bus)
        self._economy_service = economy_service or StrategicEconomyService(event_bus=event_bus)
        self._movement_service = movement_service or StrategicMovementService(
            event_bus=event_bus
        )

    async def execute_turn(
        self,
        world_state: WorldState,
        worker_assignments: Optional[dict[str, WorkerRiskTier]] = None,
    ) -> GlobalTurnReport:
        """
        Выполняет полный расчет одного глобального такта.
        """

        if self._event_bus is not None:
            await self._event_bus.publish(
                "strategic.turn_started",
                tick=world_state.time.total_ticks + 1,
                timestamp=world_state.time.format_timestamp(),
            )

        # =============================================================
        # Шаг 1. Продвижение времени, условий мира и полей брани
        # =============================================================

        events_report = await self._events_service.process_world_events(world_state)

        # =============================================================
        # Шаг 2. Расчет экономики, добычи, содержания и строек
        # =============================================================

        economy_reports = await self._economy_service.process_factions_economy(
            world_state=world_state, worker_assignments=worker_assignments
        )

        # =============================================================
        # Шаг 3. Перемещение армий, обнаружение столкновений и логистика депеш/послов
        # =============================================================

        movement_report = await self._movement_service.process_movements_and_encounters(
            world_state
        )

        # =============================================================
        # Шаг 4. Сборка итогового отчета
        # =============================================================

        final_report = GlobalTurnReport(
            events_report=events_report,
            economy_reports=economy_reports,
            movement_report=movement_report,
        )

        if self._event_bus is not None:
            await self._event_bus.publish(
                "strategic.turn_completed", # TODO: создать список типизированных событий для всех сервисов/кода
                tick=world_state.time.total_ticks,
                timestamp=events_report.current_timestamp,
                encounters_count=len(movement_report.encounters),
            )

        return final_report
