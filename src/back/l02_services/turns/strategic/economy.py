"""
Сервис расчета экономики, добычи ресурсов рабочими, списания содержания,
дефицита и прогресса строительства.
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import (
    WORKER_GOLD_YIELD_HIGH,
    WORKER_GOLD_YIELD_MODERATE,
    WORKER_GOLD_YIELD_SAFE,
    ResourceType,
    WorkerRiskTier,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState


class FactionEconomyReport(BaseModel):
    """
    Экономический отчет фракции за прошедший такт.
    """

    faction_id: str = Field(...)
    income_gold: float = Field(default=0.0)
    income_material: float = Field(default=0.0)
    income_food: float = Field(default=0.0)

    upkeep_gold_required: float = Field(default=0.0)
    upkeep_food_required: float = Field(default=0.0)

    gold_deficit: float = Field(default=0.0)
    food_deficit: float = Field(default=0.0)

    deserted_squad_names: list[str] = Field(default_factory=list)
    completed_building_names: list[str] = Field(default_factory=list)


class StrategicEconomyService:
    """
    Выполняет второй этап глобального такта: расчет добычи,
    списание содержания, дезертирство при банкротстве и завершение строек.
    """

    def __init__(self, event_bus: Optional[EventBusProtocol] = None) -> None:
        self._event_bus = event_bus

    async def process_factions_economy(
        self,
        world_state: WorldState,
        worker_assignments: Optional[dict[str, WorkerRiskTier]] = None,
    ) -> dict[str, FactionEconomyReport]:
        """
        Рассчитывает экономику для всех активных фракций в мире.
        worker_assignments: словарь {faction_id: WorkerRiskTier} (по умолчанию SAFE).
        """
        reports: dict[str, FactionEconomyReport] = {}
        assignments = worker_assignments or {}

        for faction_id, faction in world_state.factions.items():
            risk_tier = assignments.get(faction_id, WorkerRiskTier.SAFE)
            report = await self._process_single_faction_economy(
                faction=faction, world_state=world_state, risk_tier=risk_tier
            )
            reports[faction_id] = report

        return reports

    # TODO: распилить функцию
    async def _process_single_faction_economy(
        self, faction: Faction, world_state: WorldState, risk_tier: WorkerRiskTier
    ) -> FactionEconomyReport:
        """
        Рассчитывает экономику за 1 такт для одной фракции.
        """

        # =============================================================
        # Прогресс строительства
        # =============================================================

        completed_buildings = []
        for building in faction.buildings:
            if building.is_under_construction:
                if building.construction_ticks_remaining > 0:
                    building.construction_ticks_remaining -= 1

                if building.construction_ticks_remaining == 0:
                    building.complete_construction()
                    completed_buildings.append(building.building.name)
                    if self._event_bus is not None:
                        await self._event_bus.publish(
                            "strategic.building_completed",
                            faction_id=faction.id,
                            building_id=building.building.id,
                            building_name=building.building.name,
                            zone_id=building.zone_id,
                        )

        # =============================================================
        # Расчет добычи со зданий
        # =============================================================

        income_gold = 0.0
        income_material = 0.0
        income_food = 0.0

        for building in faction.buildings:
            if not building.is_under_construction:
                workers_count = len(building.assigned_worker_squad_ids)
                if workers_count > 0 and building.building.requires_workers:
                    for (
                        res_type,
                        amount,
                    ) in building.building.resource_output_per_worker.items():
                        total_output = amount * workers_count
                        if res_type == ResourceType.GOLD:
                            income_gold += total_output
                        elif res_type == ResourceType.MATERIAL:
                            income_material += total_output
                        elif res_type == ResourceType.FOOD:
                            income_food += total_output

        # =============================================================
        # Расчет добычи от свободных рабочих отрядов по уровням риска
        # =============================================================

        worker_gold_rate = WORKER_GOLD_YIELD_SAFE
        if risk_tier == WorkerRiskTier.MODERATE:
            worker_gold_rate = WORKER_GOLD_YIELD_MODERATE
        elif risk_tier == WorkerRiskTier.HIGH:
            worker_gold_rate = WORKER_GOLD_YIELD_HIGH

        # =============================================================
        # Считаем рабочих (тир 00), не привязанных к конкретным постройкам
        # =============================================================

        faction_armies = world_state.get_faction_armies(faction.id)
        free_workers_units = 0
        for army in faction_armies:
            for squad in army.squads:
                if squad.archetype.tier == 0:
                    free_workers_units += squad.state.unit_count

        # Каждый рабочий приносит часть базовой ставки за такт (1 рабочий = 1/100 отряда)
        income_gold += (free_workers_units / 100.0) * worker_gold_rate

        # Начисляем доходы в казну
        faction.earn(ResourceType.GOLD, income_gold)
        faction.earn(ResourceType.MATERIAL, income_material)
        faction.earn(ResourceType.FOOD, income_food)

        # =============================================================
        # Расчет суммарного содержания войск
        # =============================================================

        upkeep_gold_required = sum(army.total_upkeep_gold for army in faction_armies)
        upkeep_food_required = sum(army.total_upkeep_food for army in faction_armies)

        available_gold = faction.resources[ResourceType.GOLD]
        available_food = faction.resources[ResourceType.FOOD]

        gold_deficit = max(0.0, upkeep_gold_required - available_gold)
        food_deficit = max(0.0, upkeep_food_required - available_food)

        # Списываем сколько можем
        gold_to_spend = min(available_gold, upkeep_gold_required)
        food_to_spend = min(available_food, upkeep_food_required)

        faction.spend(ResourceType.GOLD, gold_to_spend)
        faction.spend(ResourceType.FOOD, food_to_spend)

        # =============================================================
        # Обработка штрафов дефицита и дезертирства
        # =============================================================

        deserted_squad_names = []
        if gold_deficit > 0 or food_deficit > 0:
            # Шок морали армии от невыплаты жалования или голода
            morale_penalty = 10.0 * (1 if gold_deficit > 0 else 0) + 15.0 * (
                1 if food_deficit > 0 else 0
            )
            for army in faction_armies:
                for squad in army.squads:
                    squad.apply_morale_shock(morale_penalty)

            if self._event_bus is not None:
                await self._event_bus.publish(
                    "strategic.famine_occurred",
                    faction_id=faction.id,
                    gold_deficit=gold_deficit,
                    food_deficit=food_deficit,
                )

            # Дезертирство: при критическом дефиците провизии (доступно < 50% от нормы)
            if food_deficit > (upkeep_food_required * 0.5):
                for army in faction_armies:
                    # Ищем отряд с наименьшей моралью или паникой
                    squad_to_desert = next(
                        (
                            s
                            for s in army.squads
                            if s.state.is_in_panic or s.state.morale < 30.0
                        ),
                        None,
                    )
                    if squad_to_desert is not None:
                        army.remove_squad(squad_to_desert.id)
                        deserted_squad_names.append(squad_to_desert.display_name)
                        if self._event_bus is not None:
                            await self._event_bus.publish(
                                "strategic.squad_deserted",
                                faction_id=faction.id,
                                squad_name=squad_to_desert.display_name,
                                army_id=army.id,
                            )
                        break

        return FactionEconomyReport(
            faction_id=faction.id,
            income_gold=income_gold,
            income_material=income_material,
            income_food=income_food,
            upkeep_gold_required=upkeep_gold_required,
            upkeep_food_required=upkeep_food_required,
            gold_deficit=gold_deficit,
            food_deficit=food_deficit,
            deserted_squad_names=deserted_squad_names,
            completed_building_names=completed_buildings,
        )
