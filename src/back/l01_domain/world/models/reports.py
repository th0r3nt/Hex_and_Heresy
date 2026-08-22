"""
Отчеты о расчете глобального (стратегического) хода.
"""

from pydantic import BaseModel, Field

from src.back.l01_domain.combat.constants import TimeOfDay
from src.back.l01_domain.combat.models.reports import MovementStepReport
from src.back.l01_domain.factions.models.economy import FactionEconomyReport


class EventsStepReport(BaseModel):
    """
    Отчет о результатах шага обновления времени и условий мира.
    """

    ticks_elapsed: int = Field(default=1)
    current_timestamp: str = Field(...)
    time_of_day: TimeOfDay = Field(...)
    is_neon_hours: bool = Field(default=False)
    phase_changed: bool = Field(default=False)

    expired_event_ids: list[str] = Field(default_factory=list)
    decayed_battlefield_ids: list[str] = Field(default_factory=list)
    recovered_hero_ids: list[str] = Field(default_factory=list)


class VeterancyServiceStepReport(BaseModel):
    """
    Отчёт о результатах шага учёта выслуги лет за один глобальный такт.
    """

    veterancy_candidate_ids: list[str] = Field(default_factory=list)


class GlobalTurnReport(BaseModel):
    """
    Итоговый структурированный отчет о расчете глобального хода.
    """

    events_report: EventsStepReport = Field(...)
    economy_reports: dict[str, FactionEconomyReport] = Field(default_factory=dict)
    movement_report: MovementStepReport = Field(...)
    completed_expedition_ids: list[str] = Field(default_factory=list)
    service_veterancy_candidate_ids: list[str] = Field(default_factory=list)
