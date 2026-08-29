"""
Фасад.
Точка входа для остальных модулей.

Оценщик умеет только считать, а фасад решает, что с посчитанным делать:
записывает финал в мир, чтобы партия закончилась ровно один раз, и объявляет
о нем на шине событий - оттуда его подхватывают и сокет, и летописец.

Своего состояния фасад не держит: и правила победы, и записанный финал лежат
в самом WorldState, поэтому один и тот же фасад одинаково годится и для шага
глобального такта, и для внеочередной проверки после штурма цитадели.
"""

from typing import Optional

from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.l01_domain.world.models.victory import (
    VictoryEvaluationResult,
    VictoryProgress,
)
from src.back.l02_services.mechanics.victory.evaluator import VictoryEvaluator
from src.back.utils.event.registry import GameEvents


class VictoryFacade:
    """
    Оркестрирует проверку глобальных целей партии и объявление ее финала.
    """

    def __init__(
        self,
        evaluator: Optional[VictoryEvaluator] = None,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._evaluator = evaluator or VictoryEvaluator()
        self._event_bus = event_bus

    # ==================================================================
    # ПРОВЕРКА МИРА
    # ==================================================================

    async def evaluate_world(self, world_state: WorldState) -> VictoryEvaluationResult:
        """
        Сверяет мир с правилами победы и, если партия закончилась, объявляет
        об этом.

        Финал наступает однажды: как только вердикт записан в мир, повторные
        проверки возвращают его же и никого не будят. Иначе каждый следующий
        такт заново трубил бы о победе, уже случившейся.
        """
        if world_state.victory_outcome is not None:
            return world_state.victory_outcome

        result = self._evaluator.evaluate(world_state)
        if not result.is_game_over:
            return result

        world_state.record_victory_outcome(result)
        await self._publish_game_over(world_state, result)

        return result

    def get_faction_progress(
        self, world_state: WorldState, faction_id: str
    ) -> VictoryProgress:
        """
        Срез продвижения фракции к целям - для панели интерфейса и советника.
        """
        return self._evaluator.calculate_progress(world_state, faction_id)

    def is_faction_defeated(self, world_state: WorldState, faction_id: str) -> bool:
        """
        Выбыла ли фракция из партии. None-фракция выбывшей не считается:
        того, кого нет на карте, побеждать не за что.
        """
        faction = world_state.get_faction(faction_id)
        if faction is None:
            return False
        return self._evaluator.is_faction_defeated(world_state, faction)

    # ==================================================================
    # ОБЪЯВЛЕНИЕ ФИНАЛА
    # ==================================================================

    async def _publish_game_over(
        self, world_state: WorldState, result: VictoryEvaluationResult
    ) -> None:
        """
        Трубит о конце партии.

        Плоские поля нужны интерфейсу, который рисует экран финала, а целый
        вердикт - летописцу: ему для финальной оды нужен и прогресс сторон.
        """
        if self._event_bus is None:
            return

        await self._event_bus.publish(
            GameEvents.GameFlow.GAME_OVER,
            is_player_victorious=result.is_player_victorious,
            victory_type=None if result.victory_type is None else result.victory_type.value,
            winner_faction_id=result.winner_faction_id,
            reason=result.reason,
            total_ticks=world_state.time.total_ticks,
            result=result,
        )
