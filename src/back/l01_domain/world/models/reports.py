"""
Отчеты о расчете глобального (стратегического) хода.
"""

from pydantic import BaseModel, Field

from src.back.l01_domain.combat.constants import TimeOfDay
from src.back.l01_domain.combat.models.reports import MovementStepReport
from src.back.l01_domain.factions.models.economy import FactionEconomyReport
from src.back.l01_domain.world.models.events import GlobalEvent


class EventsStepReport(BaseModel):
    """
    Отчет о результатах шага обновления времени и условий мира.
    """

    ticks_elapsed: int = Field(default=1)
    current_timestamp: str = Field(...)
    time_of_day: TimeOfDay = Field(...)
    is_neon_hours: bool = Field(default=False)
    phase_changed: bool = Field(default=False)

    new_events: list[GlobalEvent] = Field(
        default_factory=list, description="Новые события, запущенные на этом такте"
    )
    spawned_army_ids: list[str] = Field(
        default_factory=list, description="ID армий, появившихся на карте в результате событий"
    )

    expired_event_ids: list[str] = Field(default_factory=list)
    decayed_battlefield_ids: list[str] = Field(default_factory=list)
    recovered_hero_ids: list[str] = Field(default_factory=list)


class VeterancyServiceStepReport(BaseModel):
    """
    Отчет о результатах шага учета выслуги лет за один глобальный такт.
    """

    veterancy_candidate_ids: list[str] = Field(default_factory=list)


class GarrisonStepReport(BaseModel):
    """
    Отчет о шаге обслуживания гарнизонов земель за один глобальный такт.
    """

    raised_garrison_zone_ids: list[str] = Field(
        default_factory=list,
        description="Земли, на которых гарнизон появился впервые (новая ратуша или цитадель)",
    )
    disbanded_garrison_zone_ids: list[str] = Field(
        default_factory=list,
        description="Земли, ушедшие из-под контроля: их гарнизон снят с карты",
    )
    raised_militia_squad_ids: list[str] = Field(
        default_factory=list,
        description="Ополченцы, набранные под новые слоты после апгрейда здания",
    )
    disbanded_militia_squad_ids: list[str] = Field(
        default_factory=list,
        description="Ополченцы, распущенные по домам после падения уровня здания",
    )
    replenished_militia_squad_ids: list[str] = Field(
        default_factory=list,
        description="Ополченцы, добравшие потери за этот такт",
    )


class DiplomacyTickReport(BaseModel):
    """
    Отчет о дипломатическом шаге такта: логистика гонцов и послов, судьба пактов.
    """

    delivered_dispatch_ids: list[str] = Field(default_factory=list)
    intercepted_dispatch_ids: list[str] = Field(default_factory=list)
    arrived_ambassador_ids: list[str] = Field(default_factory=list)
    expired_pacts: list[str] = Field(
        default_factory=list,
        description="Истекшие или разорванные пакты в виде 'faction_a:faction_b:тип_пакта'",
    )


class GlobalTurnReport(BaseModel):
    """
    Итоговый структурированный отчет о расчете глобального хода.
    """

    events_report: EventsStepReport = Field(...)
    garrison_report: GarrisonStepReport = Field(default_factory=GarrisonStepReport)
    economy_reports: dict[str, FactionEconomyReport] = Field(default_factory=dict)
    movement_report: MovementStepReport = Field(...)
    diplomacy_report: DiplomacyTickReport = Field(default_factory=DiplomacyTickReport)
    completed_expedition_ids: list[str] = Field(default_factory=list)
    service_veterancy_candidate_ids: list[str] = Field(default_factory=list)
