"""
Мастер-оркестратор стратегического хода (конвейерный пайплайн).
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.combat.models.reports import MovementStepReport
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.economy import (
    FactionEconomyReport,
    StrategicEconomyService,
)
from src.back.l02_services.turns.strategic.veterancy import StrategicVeterancyService
from src.back.l02_services.turns.strategic.events import (
    EventsStepReport,
    StrategicEventsService,
)
from src.back.l02_services.turns.strategic.movement import (
    StrategicMovementService,
)
from src.back.l02_services.turns.strategic.workers.expedition import (
    ExpeditionWorkerService,
)
from src.back.utils.event.registry import GameEvents


class GlobalTurnReport(BaseModel):
    """
    Итоговый структурированный отчет о расчете глобального хода.
    """

    events_report: EventsStepReport = Field(...)
    economy_reports: dict[str, FactionEconomyReport] = Field(default_factory=dict)
    movement_report: MovementStepReport = Field(...)
    completed_expedition_ids: list[str] = Field(default_factory=list)
    service_veterancy_candidate_ids: list[str] = Field(default_factory=list)


class StrategicTurnOrchestrator:
    """
    Главный оркестратор глобального хода.
    Строго последовательно выполняет конвейер:
    [1. События и время] -> [2. Экспедиции] -> [3. Экономика и содержание] -> [4. Передвижения и логистика] -> [5. Итоговый отчет].
    """

    def __init__(
        self,
        events_service: Optional[StrategicEventsService] = None,
        economy_service: Optional[StrategicEconomyService] = None,
        movement_service: Optional[StrategicMovementService] = None,
        expedition_service: Optional[ExpeditionWorkerService] = None,
        veterancy_service: Optional[StrategicVeterancyService] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._event_bus = event_bus
        self._events_service = events_service or StrategicEventsService(event_bus=event_bus)
        self._economy_service = economy_service or StrategicEconomyService(event_bus=event_bus)
        self._movement_service = movement_service or StrategicMovementService(
            event_bus=event_bus
        )
        self._expedition_service = expedition_service or ExpeditionWorkerService(
            event_bus=event_bus
        )
        self._veterancy_service = veterancy_service or StrategicVeterancyService(
            event_bus=event_bus
        )

    async def execute_turn(
        self,
        world_state: WorldState,
    ) -> GlobalTurnReport:
        """
        Выполняет полный расчет одного глобального такта.
        """
        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Strategic.TURN_STARTED,
                tick=world_state.time.total_ticks + 1,
                timestamp=world_state.time.format_timestamp(),
            )

        # Шаг 1. Продвижение времени, условий мира и полей брани
        events_report = await self._events_service.process_world_events(world_state)

        # Шаг 1.5. Учёт выслуги лет отрядов в армиях под командованием полководцев
        service_veterancy_report = (
            await self._veterancy_service.process_service_accumulation(  # noqa: F841
                world_state
            )
        )

        # Шаг 2. Обработка экспедиций (добыча, разворот караванов, сдача груза в казну)
        completed_expeditions = await self._expedition_service.process_expeditions(world_state)

        # Шаг 3. Расчет экономики (стационарные здания, списание содержания)
        economy_reports = await self._economy_service.process_factions_economy(world_state)

        # Шаг 4. Перемещение армий и караванов, обнаружение столкновений и логистика депеш/послов
        movement_report = await self._movement_service.process_movements_and_encounters(
            world_state
        )

        # Очистка завершенных назначений
        world_state.cleanup_completed_assignments()

        # Шаг 5. Сборка итогового отчета
        final_report = GlobalTurnReport(
            events_report=events_report,
            economy_reports=economy_reports,
            movement_report=movement_report,
            completed_expedition_ids=completed_expeditions,
            service_veterancy_candidate_ids=service_veterancy_report.veterancy_candidate_ids,
        )

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Strategic.TURN_COMPLETED,
                tick=world_state.time.total_ticks,
                timestamp=events_report.current_timestamp,
                encounters_count=len(movement_report.encounters),
            )

        return final_report
