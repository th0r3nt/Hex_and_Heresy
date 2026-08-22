"""
Главный фасад оркестрации ходов (стратегических и тактических).
"""

from typing import Optional

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.combat.models.reports import TacticalTurnReport
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.exceptions import NoArmiesLockedForBattleError
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.reports import GlobalTurnReport
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.orchestrator import (
    StrategicTurnOrchestrator,
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
