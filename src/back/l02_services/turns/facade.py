"""
Главный фасад оркестрации ходов (стратегических и тактических).
"""

from typing import Optional

from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.turns.strategic.orchestrator import (
    GlobalTurnReport,
    StrategicTurnOrchestrator,
)


class TurnsFacade:
    """
    Единая точка входа для исполнения ходов игры.
    Делегирует расчет специализированным оркестраторам.
    """

    def __init__(
        self,
        strategic_orchestrator: Optional[StrategicTurnOrchestrator] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._event_bus = event_bus
        self._strategic_orchestrator = strategic_orchestrator or StrategicTurnOrchestrator(
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

    # TODO: написать логику тактических ходов
    #
    # ВАЖНО (см. VeterancyStatus.accumulate_kills): TacticalTurnOrchestrator.
    # execute_turn принимает squads: dict[str, Squad] и мутирует
    # Squad.veterancy напрямую по ссылке. Когда здесь появится связка
    # стратегия -> тактика, критично передавать в тактический оркестратор
    # ТЕ ЖЕ САМЫЕ объекты Squad, что лежат в StrategicArmy.squads — не
    # копии и не пересозданные заново из сериализованного состояния
    # (например, после круга через WebSocket/API). Если тактический слой
    # будет работать с копией, accumulated_kill_weight будет неявно
    # обнуляться после каждого боя, и вся механика персистентного счётчика
    # ветеранства сломается молча, без единой ошибки или упавшего теста —
    # существующие тесты на это свойство (см.
    # test_kill_weight_accumulates_across_separate_battle_calls) проверяют
    # только сам сервис в изоляции и не могут поймать баг на уровне
    # интеграции, которой здесь ещё нет.