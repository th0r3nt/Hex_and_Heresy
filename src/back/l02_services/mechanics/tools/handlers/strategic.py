"""
Обработчики навыков глобальной карты поверх TurnsFacade.

Держава берется из обстановки, а не из аргументов: модель распоряжается
только тем, что принадлежит ей самой.
"""

from src.back.l01_domain.llm.tools.strategic import (
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


def register_strategic_handlers(executor: ToolExecutor, turns: TurnsFacade) -> None:
    """
    Подключает навыки глобальной карты к диспетчеру.
    """

    # ==================================================================
    # АРМИИ И ЭКОНОМИКА
    # ==================================================================

    async def order_army_march(
        context: ToolExecutionContext, params: OrderArmyMarchParams
    ) -> str:
        path = turns.order_army_march(
            world_state=context.world_state,
            army_id=params.army_id,
            target_hex=params.to_target_hex(),
        )
        return f"Армия '{params.army_id}' выступила: путь в {len(path)} гексов."

    async def set_tax_rate(
        context: ToolExecutionContext, params: SetTaxRateParams
    ) -> str:
        faction = await turns.set_faction_tax_rate(
            world_state=context.world_state,
            faction_id=context.faction_id,
            rate=params.rate,
        )
        return (
            f"Ставка налога теперь {faction.tax_rate:.2f} "
            f"(режим сбора: {faction.tax_band.value})."
        )

    async def assign_worker(
        context: ToolExecutionContext, params: AssignWorkerParams
    ) -> str:
        await turns.assign_worker(
            world_state=context.world_state,
            squad_id=params.squad_id,
            faction_id=context.faction_id,
            building_id=params.building_id,
        )
        return f"Рабочие '{params.squad_id}' встали на здание '{params.building_id}'."

    async def unassign_worker(
        context: ToolExecutionContext, params: UnassignWorkerParams
    ) -> str:
        await turns.unassign_worker(
            world_state=context.world_state, squad_id=params.squad_id
        )
        return f"Рабочие '{params.squad_id}' сняты с производства."

    async def dispatch_expedition(
        context: ToolExecutionContext, params: DispatchExpeditionParams
    ) -> str:
        await turns.dispatch_expedition(
            world_state=context.world_state,
            squad_id=params.squad_id,
            faction_id=context.faction_id,
            target_hex=params.to_target_hex(),
            home_hex=params.to_home_hex(),
            mining_duration_ticks=params.mining_duration_ticks,
        )
        return (
            f"Караван '{params.squad_id}' ушел в экспедицию на "
            f"{params.mining_duration_ticks} тактов добычи."
        )

    # ==================================================================
    # ПОГРАНИЧНЫЕ ГОРОДА
    # ==================================================================

    async def found_border_town(
        context: ToolExecutionContext, params: FoundBorderTownParams
    ) -> str:
        town = await turns.found_border_town(
            world_state=context.world_state,
            faction_id=context.faction_id,
            target_hex=params.to_target_hex(),
            name=params.name,
        )
        return f"Основан пограничный город '{town.name}' (id {town.id})."

    async def upgrade_border_town(
        context: ToolExecutionContext, params: UpgradeBorderTownParams
    ) -> str:
        town = await turns.upgrade_border_town(
            world_state=context.world_state,
            faction_id=context.faction_id,
            town_id=params.town_id,
        )
        return f"Город '{town.name}' поднят до уровня {town.level}."

    async def claim_border_land(
        context: ToolExecutionContext, params: ClaimBorderLandParams
    ) -> str:
        town = await turns.claim_border_land(
            world_state=context.world_state,
            faction_id=context.faction_id,
            town_id=params.town_id,
            target_hex=params.to_target_hex(),
        )
        return f"Город '{town.name}' выкупил смежную землю и поставил на ней ратушу."

    async def resolve_border_town(
        context: ToolExecutionContext, params: ResolveBorderTownParams
    ) -> str:
        operation = await turns.resolve_border_town(
            world_state=context.world_state,
            town_id=params.town_id,
            army_id=params.army_id,
            resolution_type=params.resolution_type,
        )
        if operation is None:
            return f"Армия '{params.army_id}' прошла мимо города и свободна тем же тактом."
        return (
            f"Над городом '{params.town_id}' начата операция "
            f"'{params.resolution_type.value}': осталось тактов - "
            f"{operation.ticks_remaining}."
        )

    # ==================================================================
    # ГАРНИЗОНЫ
    # ==================================================================

    async def station_squad(
        context: ToolExecutionContext, params: StationSquadParams
    ) -> str:
        garrison = await turns.station_squad(
            world_state=context.world_state,
            army_id=params.army_id,
            squad_id=params.squad_id,
            zone_id=params.zone_id,
        )
        return (
            f"Отряд '{params.squad_id}' встал в гарнизон земли '{params.zone_id}': "
            f"карточек за стенами - {len(garrison.stationed_squads)}."
        )

    async def unstation_squad(
        context: ToolExecutionContext, params: UnstationSquadParams
    ) -> str:
        await turns.unstation_squad(
            world_state=context.world_state,
            army_id=params.army_id,
            squad_id=params.squad_id,
            zone_id=params.zone_id,
        )
        return (
            f"Отряд '{params.squad_id}' вернулся из гарнизона "
            f"'{params.zone_id}' в армию '{params.army_id}'."
        )

    executor.register(ORDER_ARMY_MARCH, order_army_march)
    executor.register(SET_TAX_RATE, set_tax_rate)
    executor.register(ASSIGN_WORKER, assign_worker)
    executor.register(UNASSIGN_WORKER, unassign_worker)
    executor.register(DISPATCH_EXPEDITION, dispatch_expedition)
    executor.register(FOUND_BORDER_TOWN, found_border_town)
    executor.register(UPGRADE_BORDER_TOWN, upgrade_border_town)
    executor.register(CLAIM_BORDER_LAND, claim_border_land)
    executor.register(RESOLVE_BORDER_TOWN, resolve_border_town)
    executor.register(STATION_SQUAD, station_squad)
    executor.register(UNSTATION_SQUAD, unstation_squad)


__all__ = ["register_strategic_handlers"]
