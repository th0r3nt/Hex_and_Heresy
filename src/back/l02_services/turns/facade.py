"""
Главный фасад оркестрации ходов (стратегических и тактических).
"""

from typing import Optional

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.combat.models.reports import TacticalTurnReport
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.exceptions.workers import InvalidAssignmentTargetError
from src.back.l01_domain.exceptions.world import NoArmiesLockedForBattleError
from src.back.l01_domain.factions.models.workers import WorkerAssignment
from src.back.l01_domain.maps.models.strategic import HexCoordinates, hex_line
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.reports import GlobalTurnReport
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.orchestrator import (
    StrategicTurnOrchestrator,
)
from src.back.l02_services.turns.strategic.workers.expedition import (
    ExpeditionWorkerService,
)
from src.back.l02_services.turns.strategic.workers.stationary import (
    StationaryWorkerService,
)
from src.back.l02_services.turns.tactical.orchestrator import TacticalTurnOrchestrator


class TurnsFacade:
    """
    Единая точка входа для исполнения ходов игры.
    Делегирует расчет специализированным оркестраторам.
    """

    def __init__(
        self,
        strategic_orchestrator: Optional[StrategicTurnOrchestrator] = None,
        tactical_orchestrator: Optional[TacticalTurnOrchestrator] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._event_bus = event_bus
        self._strategic_orchestrator = strategic_orchestrator or StrategicTurnOrchestrator(
            event_bus=event_bus
        )
        self._tactical_orchestrator = tactical_orchestrator or TacticalTurnOrchestrator(
            event_bus=event_bus
        )
        self._stationary_workers = StationaryWorkerService(event_bus=event_bus)
        self._expedition_workers = ExpeditionWorkerService(event_bus=event_bus)

    # ==================================================================
    # ПРИКАЗЫ ИГРОКА НА ГЛОБАЛЬНОЙ КАРТЕ
    # ==================================================================

    def order_army_march(
        self,
        world_state: WorldState,
        army_id: str,
        target_hex: HexCoordinates,
    ) -> list[HexCoordinates]:
        """
        Прокладывает армии маршрут до гекса. Сам марш считается тактом
        (execute_strategic_turn), здесь только выдается приказ.

        Возвращает запланированный путь без гекса, на котором армия стоит.
        """
        army = world_state.get_army(army_id)
        if army is None:
            raise InvalidAssignmentTargetError(army_id, "армия не найдена")
        if army.is_in_tactical_battle:
            raise InvalidAssignmentTargetError(army_id, "армия связана тактическим боем")

        army.target_hex = target_hex
        army.planned_path = hex_line(army.current_hex, target_hex)[1:]
        return army.planned_path

    async def assign_worker(
        self,
        world_state: WorldState,
        squad_id: str,
        faction_id: str,
        building_id: str,
    ) -> WorkerAssignment:
        """
        Ставит отряд рабочих на экономическое здание.
        """
        return await self._stationary_workers.assign_squad_to_building(
            world_state=world_state,
            squad_id=squad_id,
            faction_id=faction_id,
            building_id=building_id,
        )

    async def unassign_worker(self, world_state: WorldState, squad_id: str) -> None:
        """
        Снимает отряд рабочих с производства.
        """
        await self._stationary_workers.unassign_squad_from_building(
            world_state=world_state,
            squad_id=squad_id,
        )

    async def dispatch_expedition(
        self,
        world_state: WorldState,
        squad_id: str,
        faction_id: str,
        target_hex: HexCoordinates,
        home_hex: HexCoordinates,
        mining_duration_ticks: int,
    ) -> WorkerAssignment:
        """
        Отправляет караван рабочих в экспедицию на нейтральный гекс.
        """
        return await self._expedition_workers.dispatch_expedition(
            world_state=world_state,
            squad_id=squad_id,
            faction_id=faction_id,
            target_hex=target_hex,
            home_hex=home_hex,
            mining_duration_ticks=mining_duration_ticks,
        )

    # ==================================================================
    # РАСЧЕТ ХОДОВ
    # ==================================================================

    async def execute_strategic_turn(
        self,
        world_state: WorldState,
    ) -> GlobalTurnReport:
        """
        Выполняет расчет глобального такта стратегической карты.
        """
        return await self._strategic_orchestrator.execute_turn(world_state=world_state)

    async def execute_tactical_turn(
        self,
        world_state: WorldState,
        battle_state: TacticalBattleState,
    ) -> TacticalTurnReport:
        """
        Выполняет один тактический раунд (30 секунд) для боя battle_state.

        Собирает отряды/полководцев/героев из армий, закреплённых за этим
        боем в world_state.active_battle_armies (см. WorldState.
        lock_armies_for_battle) - те же самые объекты Squad/Commander/Hero,
        что лежат в StrategicArmy, а не их копии. Это критично для
        персистентности счётчика ветеранства (см.
        VeterancyStatus.accumulate_kills) - если бы сюда передавалась копия,
        accumulated_kill_weight неявно обнулялся бы после каждого боя.

        По завершении боя снимает лок с армий и регистрирует поле брани.
        """
        army_ids = world_state.active_battle_armies.get(battle_state.id)
        if not army_ids:
            raise NoArmiesLockedForBattleError(battle_state.id)

        squads: dict[str, Squad] = {}
        commanders: dict[str, Commander] = {}
        heroes: dict[str, Hero] = {}
        strategic_hex: Optional[HexCoordinates] = None

        for army_id in army_ids:
            army = world_state.get_army(army_id)
            if army is None:
                continue
            strategic_hex = army.current_hex
            for squad in army.squads:
                squads[squad.id] = squad
            if army.commander is not None:
                commanders[army.commander.id] = army.commander
            for hero in army.heroes:
                heroes[hero.id] = hero

        if strategic_hex is None:
            raise NoArmiesLockedForBattleError(battle_state.id)

        report = await self._tactical_orchestrator.execute_turn(
            battle_state=battle_state,
            squads=squads,
            strategic_hex=strategic_hex,
            commanders=commanders,
            heroes=heroes,
        )

        if report.is_battle_finished:
            world_state.release_armies_from_battle(battle_state.id)
            if report.loot_site is not None:
                world_state.add_battlefield_site(report.loot_site)

        return report
