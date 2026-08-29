"""
Проверка состояния мира на глобальные цели партии.

Оценщик - чистая функция от WorldState: он ничего не меняет, никого не
уведомляет и ни во что не ходит. Ему отдают мир, он возвращает вердикт.
Все побочные эффекты (событие шины, запись финала, перевод игры на экран
окончания) остаются на VictoryFacade.

Порядок проверки важен и зафиксирован:

1. поражение игрока - оно перекрывает любую его недостигнутую цель;
2. победа игрока по первой же выполненной ветке;
3. победа соперника - для игрока это тоже конец партии.
"""

from typing import Optional

from src.back.l01_domain.exceptions.factions import FactionNotFoundError
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.world.constants import VictoryType
from src.back.l01_domain.world.models.state import WorldState
from src.back.l01_domain.world.models.victory import (
    VictoryConditionConfig,
    VictoryEvaluationResult,
    VictoryProgress,
)
from src.back.l02_services.mechanics.victory.narrative import (
    describe_defeat,
    describe_player_victory,
    describe_rival_victory,
)


class VictoryEvaluator:
    """
    Сверяет состояние мира с правилами победы текущей партии.
    """

    # ==================================================================
    # ЗАМЕР ПРОГРЕССА
    # ==================================================================

    def calculate_progress(
        self, world_state: WorldState, faction_id: str
    ) -> VictoryProgress:
        """
        Снимает срез продвижения фракции ко всем трем целям.

        Замер моментальный: он показывает мир таким, какой он прямо сейчас.
        Разграбленный до второго уровня город из зачета выпадает, а
        потраченная на найм казна откатывает экономическую полоску назад.
        """
        faction = world_state.get_faction(faction_id)
        if faction is None:
            raise FactionNotFoundError(faction_id)

        config = world_state.victory_config
        enemies = self._enemies_of(world_state, faction_id)

        return VictoryProgress(
            faction_id=faction_id,
            domination_defeated_factions=sum(
                1 for enemy in enemies if self.is_faction_defeated(world_state, enemy)
            ),
            domination_total_enemies=len(enemies),
            current_gold=faction.resources.get(ResourceType.GOLD, 0.0),
            current_material=faction.resources.get(ResourceType.MATERIAL, 0.0),
            current_food=faction.resources.get(ResourceType.FOOD, 0.0),
            target_gold=config.gold_threshold,
            target_material=config.material_threshold,
            target_food=config.food_threshold,
            max_level_towns_count=sum(
                1 for town in faction.border_towns if town.level >= config.town_level
            ),
            required_towns_count=config.towns_count,
            required_town_level=config.town_level,
        )

    # ==================================================================
    # ВЫБЫВАНИЕ ФРАКЦИИ
    # ==================================================================

    def is_faction_defeated(self, world_state: WorldState, faction: Faction) -> bool:
        """
        Выбыла ли фракция из партии.

        Два разных конца. Обычный - сожженная штурмом цитадель. Второй
        страхует случай, когда цитадели фракция лишилась иначе: у нее не
        осталось ни войск, ни земель, ни производств, ни казны, и подняться
        обратно ей уже не с чего.
        """
        if faction.headquarters.is_destroyed:
            return True
        return self._is_wiped_out(world_state, faction)

    @staticmethod
    def _is_wiped_out(world_state: WorldState, faction: Faction) -> bool:
        """
        Не осталось совсем ничего: ни живой армии, ни клочка земли, ни
        здания, ни единицы ресурса.

        Условия соединены через "и" намеренно: пустая казна при живой армии -
        это тяжелый такт, а не конец партии.
        """
        has_armies = any(
            not army.is_wiped_out
            for army in world_state.get_faction_armies(faction.id)
        )
        has_lands = bool(
            faction.border_towns or faction.regional_halls or faction.controlled_zone_ids
        )
        has_production = bool(faction.buildings)
        has_treasury = any(amount > 0 for amount in faction.resources.values())

        return not (has_armies or has_lands or has_production or has_treasury)

    # ==================================================================
    # ВЕРДИКТ О ФИНАЛЕ
    # ==================================================================

    def evaluate(self, world_state: WorldState) -> VictoryEvaluationResult:
        """
        Выносит вердикт по всему миру разом.

        Партия без фракции игрока (наблюдение, отладочный мир) не
        заканчивается никогда: некому ни выигрывать, ни проигрывать -
        вердикт несет только срез прогресса сторон.
        """
        progress = {
            faction_id: self.calculate_progress(world_state, faction_id)
            for faction_id in world_state.factions
        }
        player = world_state.get_player_faction()
        if player is None:
            return VictoryEvaluationResult(progress=progress)

        config = world_state.victory_config

        # Шаг 1. Поражение важнее целей: победить, лишившись цитадели, нельзя
        if self.is_faction_defeated(world_state, player):
            return VictoryEvaluationResult(
                is_game_over=True,
                is_player_victorious=False,
                reason=describe_defeat(player),
                progress=progress,
            )

        # Шаг 2. Победа игрока по первой же выполненной ветке
        player_victory = self._reached_victory(config, progress[player.id])
        if player_victory is not None:
            return VictoryEvaluationResult(
                is_game_over=True,
                is_player_victorious=True,
                victory_type=player_victory,
                winner_faction_id=player.id,
                reason=describe_player_victory(
                    player_victory, player, progress[player.id]
                ),
                progress=progress,
            )

        # Шаг 3. Цель первым взял соперник - для игрока партия тоже окончена
        for rival in self._enemies_of(world_state, player.id):
            if self.is_faction_defeated(world_state, rival):
                continue

            rival_victory = self._reached_victory(config, progress[rival.id])
            if rival_victory is None:
                continue

            return VictoryEvaluationResult(
                is_game_over=True,
                is_player_victorious=False,
                victory_type=rival_victory,
                winner_faction_id=rival.id,
                reason=describe_rival_victory(rival_victory, rival, progress[rival.id]),
                progress=progress,
            )

        return VictoryEvaluationResult(progress=progress)

    # ==================================================================
    # ВСПОМОГАТЕЛЬНОЕ
    # ==================================================================

    @staticmethod
    def _reached_victory(
        config: VictoryConditionConfig, progress: VictoryProgress
    ) -> Optional[VictoryType]:
        """
        Первая из разыгрываемых целей, условие которой уже выполнено.

        Отключенная в лобби ветка не проверяется вовсе: набранное по ней
        богатство остается просто богатством.
        """
        for victory_type in config.enabled_types:
            if progress.is_complete(victory_type):
                return victory_type
        return None

    @staticmethod
    def _enemies_of(world_state: WorldState, faction_id: str) -> list[Faction]:
        """Все остальные стороны партии - потенциальные соперники фракции."""
        return [f for f in world_state.factions.values() if f.id != faction_id]
