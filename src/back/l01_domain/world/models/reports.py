"""
Отчеты о расчете глобального (стратегического) хода.
"""

from pydantic import BaseModel, Field

from src.back.l01_domain.combat.constants import TimeOfDay
from src.back.l01_domain.combat.models.reports import MovementStepReport
from src.back.l01_domain.factions.models.economy import FactionEconomyReport
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l01_domain.world.models.victory import VictoryEvaluationResult


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


class BorderTownResolutionStepReport(BaseModel):
    """
    Отчет о шаге операций над побежденными пограничными городами за такт.

    Городов в списках может не быть вовсе: операция длится 2-3 такта и все
    это время идет молча, а в отчет попадает только в такт своего конца.
    """

    completed_operation_ids: list[str] = Field(
        default_factory=list,
        description="Операции, отработавшие свой срок на этом такте",
    )
    razed_town_ids: list[str] = Field(
        default_factory=list, description="Города, стертые с карты вместе с землями"
    )
    pillaged_town_ids: list[str] = Field(
        default_factory=list, description="Разграбленные города, оставшиеся у хозяина"
    )
    occupied_town_ids: list[str] = Field(
        default_factory=list, description="Города, перешедшие к захватчику"
    )
    released_army_ids: list[str] = Field(
        default_factory=list,
        description="Армии победителя, освободившиеся с гекса города",
    )


class VisionStepReport(BaseModel):
    """
    Отчет о шаге пересчета тумана войны за один глобальный такт.

    Числа здесь - на фракцию: интерфейсу игрока нужен только его срез, а
    советнику и летописцу полезно знать, кого именно вскрыла разведка.
    """

    visible_hexes_by_faction: dict[str, int] = Field(
        default_factory=dict,
        description="Сколько гексов фракция просматривает на конец такта",
    )
    newly_explored_by_faction: dict[str, int] = Field(
        default_factory=dict,
        description="Сколько гексов фракция открыла впервые на этом такте",
    )
    spotted_army_ids_by_faction: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Чужие армии, впервые попавшие в поле зрения фракции на этом "
            "такте: faction_id -> army_id[]"
        ),
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
    border_town_report: BorderTownResolutionStepReport = Field(
        default_factory=BorderTownResolutionStepReport
    )
    economy_reports: dict[str, FactionEconomyReport] = Field(default_factory=dict)
    movement_report: MovementStepReport = Field(...)
    diplomacy_report: DiplomacyTickReport = Field(default_factory=DiplomacyTickReport)
    vision_report: VisionStepReport = Field(
        default_factory=VisionStepReport,
        description=(
            "Туман войны на конец такта: марши уже отработали, поэтому обзор "
            "считается по итоговым позициям армий"
        ),
    )
    completed_expedition_ids: list[str] = Field(default_factory=list)
    service_veterancy_candidate_ids: list[str] = Field(default_factory=list)
    victory_result: VictoryEvaluationResult = Field(
        default_factory=VictoryEvaluationResult,
        description=(
            "Вердикт по глобальным целям на конец такта: прогресс всех сторон "
            "и признак того, что партия закончилась"
        ),
    )
