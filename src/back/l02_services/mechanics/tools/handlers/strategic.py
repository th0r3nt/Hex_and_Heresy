"""
Обработчики навыков глобальной стратегической карты.
"""

from typing import Any

from src.back.l01_domain.llm.tools.definitions.strategic import (
    ASSIGN_WORKER,
    CLAIM_BORDER_LAND,
    DISPATCH_EXPEDITION,
    FOUND_BORDER_TOWN,
    ORDER_ARMY_MARCH,
    RESOLVE_BORDER_TOWN,
    SET_TAX_RATE,
    STATION_SQUAD,
    UNASSIGN_WORKER,
    UNSTATION_SQUAD,
    UPGRADE_BORDER_TOWN,
)
from src.back.l01_domain.llm.tools.schemas.strategic import (
    AssignWorkerParams,
    ClaimBorderLandParams,
    DispatchExpeditionParams,
    FoundBorderTownParams,
    OrderArmyMarchParams,
    ResolveBorderTownParams,
    SetTaxRateParams,
    StationSquadParams,
    UnassignWorkerParams,
    UnstationSquadParams,
    UpgradeBorderTownParams,
)
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.l02_services.turns.facade import TurnsFacade


class StrategicToolHandlers:
    """
    Ход державы на глобальной карте: марши, налоги, рабочие и пограничье.
    """

    def __init__(self, turns_facade: TurnsFacade) -> None:
        self._turns = turns_facade

    def register(self, executor: ToolExecutor) -> None:
        """
        Подключает стратегические навыки к исполнителю.
        """
        executor.register_handler(ORDER_ARMY_MARCH, self.order_army_march)
        executor.register_handler(SET_TAX_RATE, self.set_tax_rate)
        executor.register_handler(ASSIGN_WORKER, self.assign_worker)
        executor.register_handler(UNASSIGN_WORKER, self.unassign_worker)
        executor.register_handler(DISPATCH_EXPEDITION, self.dispatch_expedition)
        executor.register_handler(FOUND_BORDER_TOWN, self.found_border_town)
        executor.register_handler(UPGRADE_BORDER_TOWN, self.upgrade_border_town)
        executor.register_handler(CLAIM_BORDER_LAND, self.claim_border_land)
        executor.register_handler(RESOLVE_BORDER_TOWN, self.resolve_border_town)
        executor.register_handler(STATION_SQUAD, self.station_squad)
        executor.register_handler(UNSTATION_SQUAD, self.unstation_squad)

    # ====================================================
    # Приказы армиям и налоги
    # ====================================================

    async def order_army_march(
        self, params: OrderArmyMarchParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Отправляет армию к указанному гексу и возвращает длину маршрута.
        """
        target_hex = params.to_target_hex()
        path = self._turns.order_army_march(
            world_state=ctx.world_state,
            army_id=params.army_id,
            target_hex=target_hex,
        )
        return (
            f"Армии '{params.army_id}' отдан приказ на марш к гексу ({params.target_q}, {params.target_r}). "
            f"Длина маршрута: {len(path)} гекс.",
            {"army_id": params.army_id, "planned_path_length": len(path)},
        )

    async def set_tax_rate(
        self, params: SetTaxRateParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Меняет налоговую ставку своей державы.
        """
        faction_id = ctx.require_caller_faction_id("set_tax_rate")
        faction = await self._turns.set_faction_tax_rate(
            world_state=ctx.world_state,
            faction_id=faction_id,
            rate=params.rate,
        )
        return (
            f"Налоговая ставка фракции '{faction.name}' установлена на {faction.tax_rate:.2f} "
            f"(режим: {faction.tax_band.value}).",
            {
                "faction_id": faction.id,
                "tax_rate": faction.tax_rate,
                "band": faction.tax_band.value,
            },
        )

    # ====================================================
    # Рабочие и экспедиции
    # ====================================================

    async def assign_worker(
        self, params: AssignWorkerParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Ставит отряд рабочих на здание своей державы.
        """
        faction_id = ctx.require_caller_faction_id("assign_worker")
        assignment = await self._turns.assign_worker(
            world_state=ctx.world_state,
            squad_id=params.squad_id,
            faction_id=faction_id,
            building_id=params.building_id,
        )
        return (
            f"Отряд рабочих '{params.squad_id}' назначен на здание '{params.building_id}'. "
            f"Текущий статус: {assignment.status.value}.",
            {"assignment_id": assignment.id, "status": assignment.status.value},
        )

    async def unassign_worker(
        self, params: UnassignWorkerParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Снимает отряд рабочих с производства.
        """
        await self._turns.unassign_worker(
            world_state=ctx.world_state,
            squad_id=params.squad_id,
        )
        return (
            f"Отряд рабочих '{params.squad_id}' успешно снят с производства.",
            {"squad_id": params.squad_id},
        )

    async def dispatch_expedition(
        self, params: DispatchExpeditionParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Отправляет караван рабочих на дальний гекс добывать ресурсы.
        """
        faction_id = ctx.require_caller_faction_id("dispatch_expedition")
        assignment = await self._turns.dispatch_expedition(
            world_state=ctx.world_state,
            squad_id=params.squad_id,
            faction_id=faction_id,
            target_hex=params.to_target_hex(),
            home_hex=params.to_home_hex(),
            mining_duration_ticks=params.mining_duration_ticks,
        )
        return (
            f"Караван рабочих '{params.squad_id}' отправлен в экспедицию на гекс "
            f"({params.target_q}, {params.target_r}) на {params.mining_duration_ticks} тактов.",
            {"assignment_id": assignment.id, "army_id": assignment.expedition_army_id},
        )

    # ====================================================
    # Пограничные города
    # ====================================================

    async def found_border_town(
        self, params: FoundBorderTownParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Основывает пограничный город на указанном гексе.
        """
        faction_id = ctx.require_caller_faction_id("found_border_town")
        town = await self._turns.found_border_town(
            world_state=ctx.world_state,
            faction_id=faction_id,
            target_hex=params.to_target_hex(),
            name=params.name,
        )
        return (
            f"Основан пограничный город «{town.name}» на гексе ({params.target_q}, {params.target_r}).",
            {"town_id": town.id, "town_name": town.name, "zone_id": town.zone_id},
        )

    async def upgrade_border_town(
        self, params: UpgradeBorderTownParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Поднимает уровень пограничного города.
        """
        faction_id = ctx.require_caller_faction_id("upgrade_border_town")
        town = await self._turns.upgrade_border_town(
            world_state=ctx.world_state,
            faction_id=faction_id,
            town_id=params.town_id,
        )
        return (
            f"Пограничный город «{town.name}» улучшен до {town.level}-го уровня "
            f"(слотов для зданий: {town.building_slots}).",
            {
                "town_id": town.id,
                "level": town.level,
                "building_slots": town.building_slots,
            },
        )

    async def claim_border_land(
        self, params: ClaimBorderLandParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Присоединяет к городу смежную землю.
        """
        faction_id = ctx.require_caller_faction_id("claim_border_land")
        town = await self._turns.claim_border_land(
            world_state=ctx.world_state,
            faction_id=faction_id,
            town_id=params.town_id,
            target_hex=params.to_target_hex(),
        )
        return (
            f"Город «{town.name}» заселил смежную землю ({params.target_q}, {params.target_r}). "
            f"Осталось свободных слотов для земель: {town.free_land_slots}.",
            {"town_id": town.id, "free_land_slots": town.free_land_slots},
        )

    async def resolve_border_town(
        self, params: ResolveBorderTownParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Решает судьбу захваченного города: разграбить, сжечь или пройти мимо.
        """
        operation = await self._turns.resolve_border_town(
            world_state=ctx.world_state,
            town_id=params.town_id,
            army_id=params.army_id,
            resolution_type=params.resolution_type,
        )
        if operation is None:
            return (
                f"Победитель решил пройти мимо города '{params.town_id}', не причиняя вреда.",
                {
                    "town_id": params.town_id,
                    "resolution_type": params.resolution_type.value,
                },
            )
        return (
            f"Начата операция '{params.resolution_type.value}' над городом '{params.town_id}'. "
            f"Длительность: {operation.ticks_total} тактов.",
            {"operation_id": operation.id, "ticks_total": operation.ticks_total},
        )

    # ====================================================
    # Гарнизоны земель
    # ====================================================

    async def station_squad(
        self, params: StationSquadParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Ставит отряд полевой армии в гарнизон земли.
        """
        garrison = await self._turns.station_squad(
            world_state=ctx.world_state,
            army_id=params.army_id,
            squad_id=params.squad_id,
            zone_id=params.zone_id,
        )
        return (
            f"Отряд '{params.squad_id}' расквартирован в гарнизоне земли '{params.zone_id}'. "
            f"Осталось свободных мест для войск: {garrison.free_stationed_slots}.",
            {"zone_id": params.zone_id, "squad_id": params.squad_id},
        )

    async def unstation_squad(
        self, params: UnstationSquadParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Возвращает отряд из гарнизона в полевую армию.
        """
        squad = await self._turns.unstation_squad(
            world_state=ctx.world_state,
            army_id=params.army_id,
            squad_id=params.squad_id,
            zone_id=params.zone_id,
        )
        return (
            f"Отряд '{squad.display_name}' выведен из гарнизона '{params.zone_id}' "
            f"в полевую армию '{params.army_id}'.",
            {"army_id": params.army_id, "squad_id": squad.id},
        )
