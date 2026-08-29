"""
Мастер-оркестратор стратегического хода (конвейерный пайплайн).
"""

from typing import Optional

from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.world.models.reports import GlobalTurnReport
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.gameflow.facade import GameFlowFacade
from src.back.l02_services.mechanics.diplomacy.facade import DiplomacyFacade
from src.back.l02_services.mechanics.settlements.facade import SettlementsFacade
from src.back.l02_services.mechanics.victory.facade import VictoryFacade
from src.back.l02_services.turns.strategic.economy import StrategicEconomyService
from src.back.l02_services.turns.strategic.garrison import GarrisonService
from src.back.l02_services.turns.strategic.veterancy import StrategicVeterancyService
from src.back.l02_services.turns.strategic.events import StrategicEventsService
from src.back.l02_services.turns.strategic.movement import (
    StrategicMovementService,
)
from src.back.l02_services.turns.strategic.workers.expedition import (
    ExpeditionWorkerService,
)
from src.back.utils.event.registry import GameEvents


class StrategicTurnOrchestrator:
    """
    Главный оркестратор глобального хода.
    Строго последовательно выполняет конвейер:
    [1. События и время] -> [1.6. Судьба взятых городов] -> [1.7. Гарнизоны] -> [2. Экспедиции] -> [3. Экономика и содержание] -> [4. Передвижения] -> [4.5. Дипломатия] -> [4.8. Глобальные цели] -> [5. Итоговый отчет].
    """

    def __init__(
        self,
        events_service: Optional[StrategicEventsService] = None,
        economy_service: Optional[StrategicEconomyService] = None,
        movement_service: Optional[StrategicMovementService] = None,
        garrison_service: Optional[GarrisonService] = None,
        settlements_facade: Optional[SettlementsFacade] = None,
        expedition_service: Optional[ExpeditionWorkerService] = None,
        veterancy_service: Optional[StrategicVeterancyService] = None,
        diplomacy_facade: Optional[DiplomacyFacade] = None,
        victory_facade: Optional[VictoryFacade] = None,
        gameflow_facade: Optional[GameFlowFacade] = None,
        gamedata: Optional[GameDataRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._event_bus = event_bus
        self._events_service = events_service or StrategicEventsService(event_bus=event_bus)
        # Каталог нужен экономике, чтобы поднять на бунт настоящую толпу из gamedata
        self._economy_service = economy_service or StrategicEconomyService(
            event_bus=event_bus, gamedata=gamedata
        )
        self._movement_service = movement_service or StrategicMovementService(
            event_bus=event_bus
        )
        # Гарнизонам каталог нужен, чтобы поднять расовое ополчение из ростера
        self._garrison_service = garrison_service or GarrisonService(
            gamedata=gamedata, event_bus=event_bus
        )
        # Города, взятые штурмом: фасад один и тот же и для приказов игрока,
        # и для шага такта - состояние операций живет в самом мире
        self._settlements_facade = settlements_facade or SettlementsFacade(
            event_bus=event_bus
        )
        self._expedition_service = expedition_service or ExpeditionWorkerService(
            event_bus=event_bus
        )
        self._veterancy_service = veterancy_service or StrategicVeterancyService(
            event_bus=event_bus
        )
        # Дипломатии на такте нужны только пакты и логистика, LLM здесь не участвует
        self._diplomacy_facade = diplomacy_facade or DiplomacyFacade(event_bus=event_bus)
        # Глобальные цели партии: свой вердикт такт выносит всегда, а вот
        # переключить игру на экран финала может только игровой поток -
        # без него такт молча кладет вердикт в отчет
        self._victory_facade = victory_facade or VictoryFacade(event_bus=event_bus)
        self._gameflow_facade = gameflow_facade

    async def execute_turn(
        self,
        world_state: WorldState,
    ) -> GlobalTurnReport:
        """
        Выполняет полный расчет одного глобального такта.
        """
        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Strategic.TURN_STARTED,
                tick=world_state.time.total_ticks + 1,
                timestamp=world_state.time.format_timestamp(),
            )

        # Шаг 1. Продвижение времени, условий мира и полей брани
        events_report = await self._events_service.process_world_events(world_state)

        # Шаг 1.5. Учёт выслуги лет отрядов в армиях под командованием полководцев
        service_veterancy_report = (
            await self._veterancy_service.process_service_accumulation(  # noqa: F841
                world_state
            )
        )

        # Шаг 1.6. Судьба взятых пограничных городов: сожжение, разграбление
        # и захват. Идет до гарнизонов и экономики, чтобы добыча победителя и
        # перешедшие к нему земли учитывались уже в этом такте.
        border_town_report = await self._settlements_facade.process_town_resolutions(
            world_state
        )

        # Шаг 1.7. Гарнизоны земель: подъем ополчения под уровень зданий и
        # восполнение его потерь. Идет до экономики: содержание гарнизонов
        # списывается уже с обновленным составом.
        garrison_report = await self._garrison_service.process_garrisons(world_state)

        # Шаг 2. Обработка экспедиций (добыча, разворот караванов, сдача груза в казну)
        completed_expeditions = await self._expedition_service.process_expeditions(world_state)

        # Шаг 3. Расчет экономики (стационарные здания, списание содержания)
        economy_reports = await self._economy_service.process_factions_economy(world_state)

        # Шаг 4. Перемещение армий и караванов, обнаружение столкновений
        movement_report = await self._movement_service.process_movements_and_encounters(
            world_state
        )

        # Шаг 4.5. Дипломатия: исполнение пактов, движение гонцов и послов
        diplomacy_report = await self._diplomacy_facade.process_tick(world_state)

        # Очистка завершенных назначений
        world_state.cleanup_completed_assignments()

        # Шаг 4.8. Глобальные цели партии. Идет последним расчетным шагом:
        # и добыча, и налоги, и марши уже отработали, поэтому вердикт
        # выносится по окончательному состоянию мира на конец такта
        victory_result = await self._victory_facade.evaluate_world(world_state)
        if self._gameflow_facade is not None:
            await self._gameflow_facade.declare_victory_result(victory_result)

        # Шаг 5. Сборка итогового отчета
        final_report = GlobalTurnReport(
            events_report=events_report,
            garrison_report=garrison_report,
            border_town_report=border_town_report,
            economy_reports=economy_reports,
            movement_report=movement_report,
            diplomacy_report=diplomacy_report,
            completed_expedition_ids=completed_expeditions,
            service_veterancy_candidate_ids=service_veterancy_report.veterancy_candidate_ids,
            victory_result=victory_result,
        )

        if self._event_bus is not None:
            await self._event_bus.publish(
                GameEvents.Strategic.TURN_COMPLETED,
                tick=world_state.time.total_ticks,
                timestamp=events_report.current_timestamp,
                encounters_count=len(movement_report.encounters),
            )

        return final_report
