"""
Сервис расчета экономики, добычи ресурсов стационарными рабочими,
списания содержания, дефицита и прогресса строительства.
"""

from dataclasses import dataclass
from typing import Optional

from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.factions.constants import (
    ResourceType,
    WorkerAssignmentStatus,
)
from src.back.l01_domain.factions.models.economy import FactionEconomyReport
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState


@dataclass(frozen=True)
class _ResourceIncome:
    """Промежуточная сумма добытых за такт ресурсов, до зачисления в казну."""

    gold: float = 0.0
    material: float = 0.0
    food: float = 0.0


@dataclass(frozen=True)
class _UpkeepSettlement:
    """Итог списания содержания армий фракции за такт."""

    gold_required: float
    food_required: float
    gold_deficit: float
    food_deficit: float


class StrategicEconomyService:
    """
    Выполняет экономический этап глобального такта: продвижение разогрева рабочих,
    расчет добычи работающих зданий, списание содержания, дезертирство при голоде
    и завершение строек.
    """

    def __init__(self, event_bus: Optional[EventBusProtocol] = None) -> None:
        self._event_bus = event_bus

    async def process_factions_economy(
        self,
        world_state: WorldState,
    ) -> dict[str, FactionEconomyReport]:
        """
        Рассчитывает экономику для всех активных фракций в мире.
        """
        reports: dict[str, FactionEconomyReport] = {}

        # 1. Пофракционный расчет доходов, содержания и завершения строек
        for faction_id, faction in world_state.factions.items():
            report = await self._process_single_faction_economy(
                faction=faction, world_state=world_state
            )
            reports[faction_id] = report

        # 2. Продвижение разогрева для всех стационарных рабочих в мире (для следующего такта)
        await self._advance_worker_warmups(world_state)

        return reports

    async def _advance_worker_warmups(self, world_state: WorldState) -> None:
        """
        Продвигает таймеры разогрева рабочих. При завершении разогрева
        статус переходит в working, и отряд начинает приносить доход.
        """
        for assignment in world_state.worker_assignments.values():
            if assignment.status == WorkerAssignmentStatus.WARMING_UP:
                transitioned = assignment.advance_warmup()

                if transitioned and self._event_bus is not None:
                    await self._event_bus.publish(
                        "strategic.worker_warmup_completed",  # TODO: типизировать
                        assignment_id=assignment.id,
                        squad_id=assignment.squad_id,
                        faction_id=assignment.faction_id,
                        building_id=assignment.target_building_id,
                    )

    async def _process_single_faction_economy(
        self,
        faction: Faction,
        world_state: WorldState,
    ) -> FactionEconomyReport:
        """
        Рассчитывает экономику за 1 такт для одной конкретной фракции.
        """

        # ========================================================================
        # 1. Строительство
        # ========================================================================

        completed_buildings = await self._advance_construction(faction)

        # ========================================================================
        # 2. Доход от зданий, где работают назначенные отряды
        # ========================================================================

        building_income, working_workers_count = self._calculate_building_income(
            faction=faction, world_state=world_state
        )

        total_income = _ResourceIncome(
            gold=building_income.gold,
            material=building_income.material,
            food=building_income.food,
        )
        self._earn_income(faction, total_income)

        # ========================================================================
        # 3. Расходы на содержание, голод и дезертирство
        # ========================================================================

        faction_armies = world_state.get_faction_armies(faction.id)
        upkeep = self._settle_upkeep(faction, faction_armies)

        deserted_squad_names = await self._handle_deficit_consequences(
            faction=faction,
            faction_armies=faction_armies,
            upkeep=upkeep,
            world_state=world_state,
        )

        # ========================================================================

        return FactionEconomyReport(
            faction_id=faction.id,
            income_gold=total_income.gold,
            income_material=total_income.material,
            income_food=total_income.food,
            upkeep_gold_required=upkeep.gold_required,
            upkeep_food_required=upkeep.food_required,
            gold_deficit=upkeep.gold_deficit,
            food_deficit=upkeep.food_deficit,
            deserted_squad_names=deserted_squad_names,
            completed_building_names=completed_buildings,
            unavailable_worker_squad_ids=[],
        )

    async def _advance_construction(self, faction: Faction) -> list[str]:
        """
        Продвигает таймеры строек фракции на 1 такт и завершает готовые.
        """
        completed_buildings: list[str] = []

        for building in faction.buildings:
            if not building.is_under_construction:
                continue

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

        return completed_buildings

    def _calculate_building_income(
        self, faction: Faction, world_state: WorldState
    ) -> tuple[_ResourceIncome, int]:
        """
        Считает доход от зданий, учитывая только тех рабочих,
        чье назначение находится в активном статусе WORKING.
        """
        income_gold = 0.0
        income_material = 0.0
        income_food = 0.0
        total_working_squads = 0

        for building in faction.buildings:
            if building.is_under_construction or not building.building.requires_workers:
                continue

            # Считаем только отряды в статусе WORKING
            active_workers_count = 0
            for sq_id in building.assigned_worker_squad_ids:
                assignment = world_state.get_squad_assignment(sq_id)
                if (
                    assignment is not None
                    and assignment.status == WorkerAssignmentStatus.WORKING
                ):
                    active_workers_count += 1

            if active_workers_count == 0:
                continue

            total_working_squads += active_workers_count

            for res_type, amount in building.building.resource_output_per_worker.items():
                total_output = amount * active_workers_count
                if res_type == ResourceType.GOLD:
                    income_gold += total_output
                elif res_type == ResourceType.MATERIAL:
                    income_material += total_output
                elif res_type == ResourceType.FOOD:
                    income_food += total_output

        return (
            _ResourceIncome(gold=income_gold, material=income_material, food=income_food),
            total_working_squads,
        )

    @staticmethod
    def _earn_income(faction: Faction, income: _ResourceIncome) -> None:
        faction.earn(ResourceType.GOLD, income.gold)
        faction.earn(ResourceType.MATERIAL, income.material)
        faction.earn(ResourceType.FOOD, income.food)

    @staticmethod
    def _settle_upkeep(
        faction: Faction, faction_armies: list[StrategicArmy]
    ) -> _UpkeepSettlement:
        """
        Списывает доступное золото и провизию за содержание всех армий фракции.
        """
        upkeep_gold_required = sum(army.total_upkeep_gold for army in faction_armies)
        upkeep_food_required = sum(army.total_upkeep_food for army in faction_armies)

        available_gold = faction.resources[ResourceType.GOLD]
        available_food = faction.resources[ResourceType.FOOD]

        gold_deficit = max(0.0, upkeep_gold_required - available_gold)
        food_deficit = max(0.0, upkeep_food_required - available_food)

        gold_to_spend = min(available_gold, upkeep_gold_required)
        food_to_spend = min(available_food, upkeep_food_required)

        faction.spend(ResourceType.GOLD, gold_to_spend)
        faction.spend(ResourceType.FOOD, food_to_spend)

        return _UpkeepSettlement(
            gold_required=upkeep_gold_required,
            food_required=upkeep_food_required,
            gold_deficit=gold_deficit,
            food_deficit=food_deficit,
        )

    async def _handle_deficit_consequences(
        self,
        faction: Faction,
        faction_armies: list[StrategicArmy],
        upkeep: _UpkeepSettlement,
        world_state: WorldState,
    ) -> list[str]:
        """
        При дефиците бьет по морали всех отрядов и инициирует дезертирство при сильном голоде.
        Если дезертирует рабочий отряд, его назначение автоматически аннулируется.
        """
        if upkeep.gold_deficit <= 0 and upkeep.food_deficit <= 0:
            return []

        morale_penalty = 10.0 * (1 if upkeep.gold_deficit > 0 else 0) + 15.0 * (
            1 if upkeep.food_deficit > 0 else 0
        )
        for army in faction_armies:
            for squad in army.squads:
                squad.apply_morale_shock(morale_penalty)

        if self._event_bus is not None:
            await self._event_bus.publish(
                "strategic.famine_occurred",
                faction_id=faction.id,
                gold_deficit=upkeep.gold_deficit,
                food_deficit=upkeep.food_deficit,
            )

        deserted_squad_names: list[str] = []
        if upkeep.food_deficit > (upkeep.food_required * 0.5):
            for army in faction_armies:
                squad_to_desert = next(
                    (s for s in army.squads if s.state.is_in_panic or s.state.morale < 30.0),
                    None,
                )
                if squad_to_desert is None:
                    continue

                # Снимаем назначение, если сбежал рабочий
                assignment = world_state.get_squad_assignment(squad_to_desert.id)
                if assignment is not None:
                    assignment.abort()

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

        return deserted_squad_names
