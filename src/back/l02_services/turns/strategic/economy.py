"""
Сервис расчета экономики, добычи ресурсов стационарными рабочими,
списания содержания, дефицита и прогресса строительства.
"""

from dataclasses import dataclass
from random import Random
from typing import Final, Optional
from uuid import uuid4

from src.back.l01_domain.army.constants import StrategicMovementPace, UnitSizeCategory
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import (
    STATIONARY_WARMUP_TICKS,
    ResourceType,
    WorkerAssignmentStatus,
    WorkerAssignmentType,
)
from src.back.l01_domain.factions.models.economy import FactionEconomyReport
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.garrison import Garrison
from src.back.l01_domain.maps.constants import ALLIED_LANDS_RING_RADIUS
from src.back.l01_domain.maps.models.strategic import HexCoordinates, hex_ring
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.event.registry import GameEvents

# Кем выходят на карту доведенные поборами крестьяне
RIOT_UNIT_ARCHETYPE_ID: Final[str] = "unit_neu_rebels_mob_00"
RIOT_ARMY_NAME: Final[str] = "Восставшие налогоплательщики"


@dataclass(frozen=True)
class _ResourceIncome:
    """Промежуточная сумма добытых за такт ресурсов, до зачисления в казну."""

    gold: float = 0.0
    material: float = 0.0
    food: float = 0.0


@dataclass(frozen=True)
class _UpkeepSettlement:
    """Итог списания содержания армий и гарнизонов фракции за такт."""

    gold_required: float
    food_required: float
    gold_deficit: float
    food_deficit: float
    garrison_gold_required: float = 0.0
    garrison_food_required: float = 0.0


class StrategicEconomyService:
    """
    Выполняет экономический этап глобального такта: расчет добычи работающих зданий,
    списание содержания, дезертирство при голоде, завершение строек и продвижение разогрева рабочих.
    """

    def __init__(
        self,
        event_bus: Optional[EventBusProtocol] = None,
        gamedata: Optional[GameDataRepositoryProtocol] = None,
        rng: Optional[Random] = None,
    ) -> None:
        self._event_bus = event_bus
        self._gamedata = gamedata
        self._rng = rng or Random()

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

        # 3. Последствия налоговой политики: настроения, забастовки и бунты.
        # Идет после разогрева, иначе объявленная забастовка снималась бы
        # тем же тактом, в котором началась.
        for faction_id, faction in world_state.factions.items():
            await self._apply_tax_consequences(
                faction=faction, world_state=world_state, report=reports[faction_id]
            )

        return reports

    async def _advance_worker_warmups(self, world_state: WorldState) -> None:
        """
        Продвигает таймеры разогрева рабочих. При завершении разогрева
        статус переходит в working, и отряд начинает приносить доход со следующего такта.
        """
        for assignment in world_state.worker_assignments.values():
            if assignment.status == WorkerAssignmentStatus.WARMING_UP:
                transitioned = assignment.advance_warmup()
                if transitioned and self._event_bus is not None:
                    await self._event_bus.publish(
                        GameEvents.Economy.WORKER_WARMUP_COMPLETED,
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
        # 1. Строительство
        completed_buildings = await self._advance_construction(faction)

        # 2. Доход от зданий, где работают назначенные отряды, и налоговый сбор
        building_income, _ = self._calculate_building_income(
            faction=faction, world_state=world_state
        )
        tax_income_gold = await self._collect_taxes(faction)

        total_income = _ResourceIncome(
            gold=building_income.gold + tax_income_gold,
            material=building_income.material,
            food=building_income.food,
        )
        self._earn_income(faction, total_income)

        # 3. Расходы на содержание, голод и дезертирство
        faction_armies = world_state.get_faction_armies(faction.id)
        faction_garrisons = world_state.get_faction_garrisons(faction.id)
        upkeep = self._settle_upkeep(faction, faction_armies, faction_garrisons)

        deserted_squad_names = await self._handle_deficit_consequences(
            faction=faction,
            faction_armies=faction_armies,
            faction_garrisons=faction_garrisons,
            upkeep=upkeep,
            world_state=world_state,
        )

        return FactionEconomyReport(
            faction_id=faction.id,
            income_gold=total_income.gold,
            tax_income_gold=tax_income_gold,
            tax_rate=faction.tax_rate,
            income_material=total_income.material,
            income_food=total_income.food,
            upkeep_gold_required=upkeep.gold_required,
            upkeep_food_required=upkeep.food_required,
            garrison_upkeep_gold=upkeep.garrison_gold_required,
            garrison_upkeep_food=upkeep.garrison_food_required,
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
                        GameEvents.Economy.BUILDING_COMPLETED,
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
        faction: Faction,
        faction_armies: list[StrategicArmy],
        faction_garrisons: list[Garrison],
    ) -> _UpkeepSettlement:
        """
        Списывает доступное золото и провизию за содержание армий и гарнизонов.

        Жалование за стенами то же, что и в поле, а вот провизии гарнизон ест
        меньше: скидку считает сам агрегат Garrison (см. total_upkeep_food).
        """
        garrison_gold_required = sum(g.total_upkeep_gold for g in faction_garrisons)
        garrison_food_required = sum(g.total_upkeep_food for g in faction_garrisons)

        upkeep_gold_required = (
            sum(army.total_upkeep_gold for army in faction_armies) + garrison_gold_required
        )
        upkeep_food_required = (
            sum(army.total_upkeep_food for army in faction_armies) + garrison_food_required
        )

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
            garrison_gold_required=garrison_gold_required,
            garrison_food_required=garrison_food_required,
        )

    async def _handle_deficit_consequences(
        self,
        faction: Faction,
        faction_armies: list[StrategicArmy],
        faction_garrisons: list[Garrison],
        upkeep: _UpkeepSettlement,
        world_state: WorldState,
    ) -> list[str]:
        """
        При дефиците бьет по морали всех отрядов и инициирует дезертирство при сильном голоде.
        Если дезертирует рабочий, его назначение автоматически аннулируется.

        Пустая казна портит настроение и за стенами, но дезертируют только
        полевые армии: ополчение стоит на своей земле и бежать ему некуда,
        а расквартированные войска сидят на городских запасах.
        """
        if upkeep.gold_deficit <= 0 and upkeep.food_deficit <= 0:
            return []

        morale_penalty = 10.0 * (1 if upkeep.gold_deficit > 0 else 0) + 15.0 * (
            1 if upkeep.food_deficit > 0 else 0
        )
        for army in faction_armies:
            for squad in army.squads:
                squad.apply_morale_shock(morale_penalty)
        for garrison in faction_garrisons:
            for squad in garrison.all_squads:
                squad.apply_morale_shock(morale_penalty)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.FAMINE_OCCURRED,
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

                assignment = world_state.get_squad_assignment(squad_to_desert.id)
                if assignment is not None:
                    assignment.abort()

                army.remove_squad(squad_to_desert.id)
                deserted_squad_names.append(squad_to_desert.display_name)

                if self._event_bus is not None:
                    await self._event_bus.publish(
                        GameEvents.Economy.SQUAD_DESERTED,
                        faction_id=faction.id,
                        squad_name=squad_to_desert.display_name,
                        army_id=army.id,
                    )

        return deserted_squad_names

    # ====================================================
    # НАЛОГИ И НАСТРОЕНИЯ ПОДДАННЫХ
    # ====================================================

    async def _collect_taxes(self, faction: Faction) -> float:
        """
        Собирает подушный налог с цитадели и союзных ратуш по текущей ставке.
        Возвращает золото, которое зачисляется в общий доход такта.
        """
        tax_income = faction.tax_income_gold
        if tax_income <= 0:
            return 0.0

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.TAXES_COLLECTED,
                faction_id=faction.id,
                tax_rate=faction.tax_rate,
                band=faction.tax_band.value,
                gold=tax_income,
            )

        return tax_income

    async def _apply_tax_consequences(
        self,
        faction: Faction,
        world_state: WorldState,
        report: FactionEconomyReport,
    ) -> None:
        """
        Отыгрывает реакцию подданных на ставку: настроение гарнизонов,
        забастовки на производстве и бунт в союзных землях.
        """
        effects = faction.tax_effects
        rate = faction.tax_rate

        morale_delta = effects.morale_delta(rate)
        self._apply_garrison_morale(faction, world_state, morale_delta)
        report.tax_morale_delta = morale_delta

        report.striking_worker_squad_ids = await self._trigger_worker_strikes(
            faction=faction, world_state=world_state, strike_chance=effects.strike_chance
        )

        riot_army = await self._trigger_tax_riot(
            faction=faction, world_state=world_state, riot_chance=effects.riot_chance(rate)
        )
        report.riot_army_id = riot_army.id if riot_army is not None else None

    @staticmethod
    def _apply_garrison_morale(
        faction: Faction, world_state: WorldState, morale_delta: float
    ) -> None:
        """
        Разносит настроение по войскам фракции: льготы поднимают мораль,
        поборы ее роняют. Гарнизоны реагируют острее всех - они стоят прямо
        среди обираемых подданных, - но математически эффект тот же.
        """
        if morale_delta == 0:
            return

        squads = [
            squad
            for army in world_state.get_faction_armies(faction.id)
            for squad in army.squads
        ]
        squads.extend(
            squad
            for garrison in world_state.get_faction_garrisons(faction.id)
            for squad in garrison.all_squads
        )

        for squad in squads:
            if morale_delta > 0:
                squad.recover_morale(morale_delta)
            else:
                squad.apply_morale_shock(abs(morale_delta))

    async def _trigger_worker_strikes(
        self,
        faction: Faction,
        world_state: WorldState,
        strike_chance: float,
    ) -> list[str]:
        """
        Бросает проверку забастовки для каждого работающего отряда фракции.
        Бастующий бросает станок и заново разогревается перед возвратом к добыче.
        """
        if strike_chance <= 0:
            return []

        striking_squad_ids: list[str] = []

        for assignment in world_state.get_faction_worker_assignments(faction.id):
            is_working_stationary = (
                assignment.assignment_type == WorkerAssignmentType.STATIONARY
                and assignment.status == WorkerAssignmentStatus.WORKING
            )
            if not is_working_stationary or self._rng.random() >= strike_chance:
                continue

            assignment.status = WorkerAssignmentStatus.WARMING_UP
            assignment.warmup_ticks_remaining = STATIONARY_WARMUP_TICKS
            striking_squad_ids.append(assignment.squad_id)

        if striking_squad_ids and self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.WORKERS_ON_STRIKE,
                faction_id=faction.id,
                tax_rate=faction.tax_rate,
                squad_ids=striking_squad_ids,
            )

        return striking_squad_ids

    async def _trigger_tax_riot(
        self,
        faction: Faction,
        world_state: WorldState,
        riot_chance: float,
    ) -> Optional[StrategicArmy]:
        """
        Бросает проверку бунта. При провале на случайной союзной земле
        поднимается нейтральная армия восставших.
        """
        if riot_chance <= 0 or self._rng.random() >= riot_chance:
            return None

        spawn_hex = self._pick_riot_hex(faction)
        if spawn_hex is None:
            return None

        army = StrategicArmy(
            id=f"army_riot_{uuid4().hex[:8]}",
            faction_id="neutrals",
            name=RIOT_ARMY_NAME,
            current_hex=spawn_hex,
            pace=StrategicMovementPace.MARCH,
        )
        army.add_squad(self._build_rioters_squad())
        world_state.add_army(army)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.TAX_RIOT_ERUPTED,
                faction_id=faction.id,
                tax_rate=faction.tax_rate,
                army_id=army.id,
                hex=spawn_hex.model_dump(),
            )

        return army

    def _pick_riot_hex(self, faction: Faction) -> Optional[HexCoordinates]:
        """
        Выбирает случайную союзную землю вокруг цитадели под очаг восстания.
        Без известной столицы бунтовать негде.
        """
        if faction.capital_hex is None:
            return None

        allied_hexes = hex_ring(faction.capital_hex, ALLIED_LANDS_RING_RADIUS)
        if not allied_hexes:
            return None

        return self._rng.choice(allied_hexes)

    def _build_rioters_squad(self) -> Squad:
        """
        Собирает толпу бунтовщиков из каталога, а без каталога - по резервному шаблону.
        """
        archetype = (
            self._gamedata.get_unit_archetype(RIOT_UNIT_ARCHETYPE_ID)
            if self._gamedata is not None
            else None
        )

        if archetype is None:
            archetype = UnitArchetype(
                id=RIOT_UNIT_ARCHETYPE_ID,
                race=FactionRace.NEUTRALS,
                faction_id="neutrals",
                name="Толпа бунтовщиков",
                tier=0,
                default_unit_count=120,
                base_stats=BaseUnitStats(
                    max_hp=10.0, base_morale=35.0, size_category=UnitSizeCategory.MEDIUM
                ),
            )

        return Squad.create_new(archetype=archetype)
