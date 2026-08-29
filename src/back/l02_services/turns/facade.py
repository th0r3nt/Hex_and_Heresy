"""
Главный фасад оркестрации ходов (стратегических и тактических).
"""

from typing import Optional

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.combat.models.reports import TacticalTurnReport
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.exceptions.factions import (
    FactionNotFoundError,
    GarrisonNotFoundError,
)
from src.back.l01_domain.exceptions.workers import InvalidAssignmentTargetError
from src.back.l01_domain.exceptions.world import NoArmiesLockedForBattleError
from src.back.l01_domain.factions.constants import BorderTownResolutionType
from src.back.l01_domain.factions.models.border_town import (
    BorderTown,
    BorderTownOperation,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.garrison import Garrison
from src.back.l01_domain.factions.models.workers import WorkerAssignment
from src.back.l01_domain.maps.constants import HexVisibilityState
from src.back.l01_domain.maps.models.strategic import HexCoordinates, hex_line
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.world.models.reports import GlobalTurnReport
from src.back.l01_domain.world.models.state import WorldState
from src.back.l01_domain.world.models.victory import VictoryProgress
from src.back.l01_domain.world.models.visibility import FactionVisionMap
from src.back.l02_services.mechanics.settlements.facade import SettlementsFacade
from src.back.l02_services.mechanics.victory.facade import VictoryFacade
from src.back.l02_services.mechanics.vision.facade import VisionFacade
from src.back.l02_services.turns.strategic.garrison import GarrisonService
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
from src.back.utils.event.registry import GameEvents


class TurnsFacade:
    """
    Единая точка входа для исполнения ходов игры.
    Делегирует расчет специализированным оркестраторам.
    """

    def __init__(
        self,
        strategic_orchestrator: Optional[StrategicTurnOrchestrator] = None,
        tactical_orchestrator: Optional[TacticalTurnOrchestrator] = None,
        victory_facade: Optional[VictoryFacade] = None,
        vision_facade: Optional[VisionFacade] = None,
        gamedata: Optional[GameDataRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._event_bus = event_bus
        # Тот же фасад целей, что стоит шагом 4.8 в конвейере такта: своего
        # состояния он не держит, поэтому годится и для чтения прогресса
        self._victory = victory_facade or VictoryFacade(event_bus=event_bus)
        # Тот же фасад тумана, что стоит шагом 4.6 в конвейере такта: маски
        # видимости живут в самом мире, поэтому он же отдает срез карты игроку
        self._vision = vision_facade or VisionFacade(event_bus=event_bus)
        self._strategic_orchestrator = strategic_orchestrator or StrategicTurnOrchestrator(
            victory_facade=self._victory,
            vision_facade=self._vision,
            gamedata=gamedata,
            event_bus=event_bus,
        )
        self._tactical_orchestrator = tactical_orchestrator or TacticalTurnOrchestrator(
            event_bus=event_bus
        )
        self._stationary_workers = StationaryWorkerService(event_bus=event_bus)
        self._expedition_workers = ExpeditionWorkerService(event_bus=event_bus)
        self._garrisons = GarrisonService(gamedata=gamedata, event_bus=event_bus)
        self._settlements = SettlementsFacade(event_bus=event_bus)

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
        if army.is_busy_with_operation:
            raise InvalidAssignmentTargetError(
                army_id, "армия занята операцией над взятым городом"
            )

        army.target_hex = target_hex
        army.planned_path = hex_line(army.current_hex, target_hex)[1:]
        return army.planned_path

    async def set_faction_tax_rate(
        self,
        world_state: WorldState,
        faction_id: str,
        rate: float,
    ) -> Faction:
        """
        Двигает ползунок налога фракции. Новая ставка вступает в силу
        со следующего глобального такта, когда экономика соберет сбор.
        """
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise FactionNotFoundError(faction_id)

        previous_rate = faction.tax_rate
        faction.set_tax_rate(rate)

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Economy.TAX_RATE_CHANGED,
                faction_id=faction.id,
                previous_rate=previous_rate,
                rate=faction.tax_rate,
                band=faction.tax_band.value,
            )

        return faction

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
    # ПОГРАНИЧНЫЕ ГОРОДА
    # ==================================================================

    async def found_border_town(
        self,
        world_state: WorldState,
        faction_id: str,
        target_hex: HexCoordinates,
        name: str,
    ) -> BorderTown:
        """
        Основывает пограничный город на свободном гексе карты.
        """
        return await self._settlements.found_border_town(
            world_state=world_state,
            faction_id=faction_id,
            target_hex=target_hex,
            name=name,
        )

    async def upgrade_border_town(
        self,
        world_state: WorldState,
        faction_id: str,
        town_id: str,
    ) -> BorderTown:
        """
        Поднимает пограничный город на уровень выше.
        """
        return await self._settlements.upgrade_border_town(
            world_state=world_state,
            faction_id=faction_id,
            town_id=town_id,
        )

    async def claim_border_land(
        self,
        world_state: WorldState,
        faction_id: str,
        town_id: str,
        target_hex: HexCoordinates,
    ) -> BorderTown:
        """
        Выкупает городу смежную землю и ставит на ней ратушу.
        """
        return await self._settlements.claim_border_land(
            world_state=world_state,
            faction_id=faction_id,
            town_id=town_id,
            target_hex=target_hex,
        )

    def list_border_towns(
        self, world_state: WorldState, faction_id: str
    ) -> list[BorderTown]:
        """
        Все пограничные города фракции для окна управления державой.
        """
        return self._settlements.list_border_towns(
            world_state=world_state, faction_id=faction_id
        )

    async def resolve_border_town(
        self,
        world_state: WorldState,
        town_id: str,
        army_id: str,
        resolution_type: BorderTownResolutionType,
    ) -> Optional[BorderTownOperation]:
        """
        Решает судьбу взятого штурмом города: сжечь, разграбить, занять или
        пройти мимо.

        Возвращает заведенную операцию либо None, если победитель прошел
        мимо: за пропуском ждать нечего, армия свободна тем же тактом.
        """
        return await self._settlements.initiate_town_resolution(
            world_state=world_state,
            town_id=town_id,
            army_id=army_id,
            resolution_type=resolution_type,
        )

    def get_border_town_operation(
        self, world_state: WorldState, town_id: str
    ) -> Optional[BorderTownOperation]:
        """
        Прогресс операции над городом для окна осады. None - город не разоряют.
        """
        return self._settlements.get_town_operation(
            world_state=world_state, town_id=town_id
        )

    # ==================================================================
    # ГАРНИЗОНЫ ЗЕМЕЛЬ
    # ==================================================================

    async def station_squad(
        self,
        world_state: WorldState,
        army_id: str,
        squad_id: str,
        zone_id: str,
    ) -> Garrison:
        """
        Оставляет отряд армии за стенами земли. Армия должна стоять на гексе
        гарнизона, а самих карточек за стенами - не больше лимита.
        """
        return await self._garrisons.station_squad(
            world_state=world_state,
            army_id=army_id,
            squad_id=squad_id,
            zone_id=zone_id,
        )

    async def unstation_squad(
        self,
        world_state: WorldState,
        army_id: str,
        squad_id: str,
        zone_id: str,
    ) -> Squad:
        """
        Забирает расквартированный отряд обратно в мобильную армию.
        """
        return await self._garrisons.unstation_squad(
            world_state=world_state,
            army_id=army_id,
            squad_id=squad_id,
            zone_id=zone_id,
        )

    @staticmethod
    def get_garrison(world_state: WorldState, zone_id: str) -> Garrison:
        """
        Текущий состав гарнизона земли для окна управления зоной.
        """
        garrison = world_state.get_garrison(zone_id)
        if garrison is None:
            raise GarrisonNotFoundError(zone_id)
        return garrison

    # ==================================================================
    # ГЛОБАЛЬНЫЕ ЦЕЛИ ПАРТИИ
    # ==================================================================

    def get_victory_progress(
        self, world_state: WorldState, faction_id: str
    ) -> VictoryProgress:
        """
        Насколько фракция продвинулась к победе - для панели глобальных целей.
        """
        return self._victory.get_faction_progress(
            world_state=world_state, faction_id=faction_id
        )

    def is_faction_defeated(self, world_state: WorldState, faction_id: str) -> bool:
        """
        Выбыла ли фракция из партии: цитадель пала или от державы ничего
        не осталось.
        """
        return self._victory.is_faction_defeated(
            world_state=world_state, faction_id=faction_id
        )

    # ==================================================================
    # ТУМАН ВОЙНЫ
    # ==================================================================

    def get_faction_vision(
        self, world_state: WorldState, faction_id: str
    ) -> FactionVisionMap:
        """
        Маска тумана фракции: что она видит сейчас и что успела открыть.
        """
        return self._vision.get_vision_map(world_state=world_state, faction_id=faction_id)

    def get_hex_visibility(
        self, world_state: WorldState, faction_id: str, coord: HexCoordinates
    ) -> HexVisibilityState:
        """
        Состояние одного гекса глазами фракции - для подсказок интерфейса.
        """
        return self._vision.get_hex_status(
            world_state=world_state, faction_id=faction_id, coord=coord
        )

    def is_hex_visible(
        self, world_state: WorldState, faction_id: str, coord: HexCoordinates
    ) -> bool:
        """
        Просматривает ли фракция гекс прямо сейчас.
        """
        return self._vision.is_hex_visible(
            world_state=world_state, faction_id=faction_id, coord=coord
        )

    def get_world_view(self, world_state: WorldState, faction_id: str) -> WorldState:
        """
        Срез мира глазами фракции: без чужих армий, гонцов и неоткрытых земель.
        """
        return self._vision.build_world_view(
            world_state=world_state, faction_id=faction_id
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
        боем в world_state.active_battle_armies - 
        те же самые объекты Squad/Commander/Hero,
        что лежат в StrategicArmy, а не их копии. Это критично для
        персистентности счётчика ветеранства - если бы сюда передавалась копия,
        accumulated_kill_weight неявно обнулялся бы после каждого боя.

        Если бой идет на гексе с гарнизоном (цитадель, город или союзная
        земля), к защитникам добавляется весь его состав: ополчение и
        расквартированные войска дерутся вместе с мобильной армией.

        По завершении боя снимает лок с армий и гарнизона и регистрирует
        поле брани.
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

        # Гарнизон земли встает в строй рядом с армиями: те же объекты Squad,
        # что лежат в самом гарнизоне, - иначе потери штурма не сохранились бы
        for squad in self._garrisons.collect_defenders(world_state, strategic_hex):
            squads[squad.id] = squad

        report = await self._tactical_orchestrator.execute_turn(
            battle_state=battle_state,
            squads=squads,
            strategic_hex=strategic_hex,
            commanders=commanders,
            heroes=heroes,
        )

        if report.is_battle_finished:
            world_state.release_armies_from_battle(battle_state.id)
            world_state.release_garrisons_from_battle(battle_state.id)
            if report.loot_site is not None:
                world_state.add_battlefield_site(report.loot_site)

        return report
