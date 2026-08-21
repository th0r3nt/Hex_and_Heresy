"""
Сервис учёта выслуги лет — второй, независимый от боевых убийств триггер
ветеранства.
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.constants import HOURS_PER_DAY
from src.back.l01_domain.world.models.state import WorldState


class VeterancyServiceStepReport(BaseModel):
    """
    Отчёт о результатах шага учёта выслуги лет за один глобальный такт.
    """

    veterancy_candidate_ids: list[str] = Field(default_factory=list)


class StrategicVeterancyService:
    """
    Раз в глобальный такт начисляет каждому отряду в армии под командованием
    полководца выслугу в игровых сутках (VeterancyStatus.accumulate_service).

    Отряды в армиях без назначенного полководца (гарнизоны, безхозные
    армии) выслугу не копят — по лору такая армия не
    считается находящейся "под командованием", а критерий явно про службу
    именно в армии полководца.

    Начисление не зависит от того, связана ли армия тактическим боем в этот
    такт (is_in_tactical_battle) — служба идёт независимо от боевой
    активности конкретного такта.
    """

    def __init__(self, event_bus: Optional[EventBusProtocol] = None) -> None:
        self._event_bus = event_bus

    async def process_service_accumulation(
        self, world_state: WorldState
    ) -> VeterancyServiceStepReport:
        """
        Начисляет выслугу всем отрядам всех армий с полководцем и собирает
        список отрядов, впервые пересёкших порог именно этим тактом.
        """
        days_elapsed = world_state.time.hours_per_tick / HOURS_PER_DAY

        candidate_ids: list[str] = []

        for army in world_state.armies.values():
            if army.commander is None:
                continue

            for squad in army.squads:
                if squad.state.unit_count <= 0 or squad.veterancy.is_named:
                    continue

                if squad.veterancy.accumulate_service(days_elapsed):
                    candidate_ids.append(squad.id)

        return VeterancyServiceStepReport(veterancy_candidate_ids=candidate_ids)
