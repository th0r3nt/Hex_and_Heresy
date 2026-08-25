"""
Сохраняет глобальное состояние игры и сохраняет в базу данных.

Обертка подготовки WorldState к записи: снимает независимую копию агрегата,
подчищает истекшие сущности и собирает метаданные для меню загрузки.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from src.back.l01_domain.exceptions.saves import EmptySaveNameError, SaveDuringBattleForbiddenError
from src.back.l01_domain.world.models.saves import SaveMetadata, SaveSnapshot
from src.back.l01_domain.world.models.state import WorldState


class WorldStateDumper:
    """
    Готовит WorldState к сохранению.

    Работает только с доменным агрегатом и ничего не знает о том, куда именно
    уедет снимок: сериализация в JSON и запись остаются за инфраструктурой,
    реализующей SaveGameRepositoryProtocol.
    """

    def prepare(
        self,
        world_state: WorldState,
        save_name: str,
        save_id: Optional[str] = None,
    ) -> SaveSnapshot:
        """
        Собирает снимок партии: проверяет допустимость сохранения, делает
        глубокую копию состояния, вычищает отработавшие сущности и считает
        метаданные.

        Копия критична: партия продолжает жить после вызова, и мутации
        WorldState не должны просачиваться в еще не записанный снимок.
        """
        name = save_name.strip()
        if not name:
            raise EmptySaveNameError()

        self.assert_can_dump(world_state)

        snapshot = world_state.model_copy(deep=True)
        self._sanitize(snapshot)

        return SaveSnapshot(
            metadata=self.build_metadata(snapshot, save_id=save_id or str(uuid4()), save_name=name),
            state=snapshot,
        )

    def assert_can_dump(self, world_state: WorldState) -> None:
        """
        Запрещает сохранение, пока за партией числятся незавершенные тактические бои.

        Тактический бой живет в отдельном TacticalBattleState, который в снимок
        не попадает: записав WorldState посреди сражения, мы получили бы сейв с
        намертво залоченными армиями и потерянным полем боя.
        """
        if world_state.active_battle_armies:
            raise SaveDuringBattleForbiddenError(list(world_state.active_battle_armies.keys()))

    def build_metadata(
        self, world_state: WorldState, save_id: str, save_name: str
    ) -> SaveMetadata:
        """
        Вычисляет описание партии для витрины сохранений.
        """
        player_faction = world_state.get_player_faction()

        return SaveMetadata(
            save_id=save_id,
            save_name=save_name,
            created_at=datetime.now(timezone.utc),
            total_ticks=world_state.time.total_ticks,
            current_day=world_state.time.current_day,
            current_year=world_state.time.current_year,
            player_faction_name=player_faction.name if player_faction is not None else None,
            factions_count=len(world_state.factions),
            armies_count=len(world_state.armies),
            custom_equipment_count=len(world_state.custom_equipment),
        )

    def _sanitize(self, snapshot: WorldState) -> None:
        """
        Вычищает из снимка мусор, который не должен переживать загрузку:
        истекшие события, вычерпанные поля брани и отработавшие назначения рабочих.
        """
        snapshot.cleanup_expired_events()
        snapshot.cleanup_depleted_battlefields()
        snapshot.cleanup_completed_assignments()
