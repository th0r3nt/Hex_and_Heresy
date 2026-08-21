"""
Сервис поклеточного перемещения отрядов, учета ландшафта,
коллизий, расхода выносливости и маршрутов бегства.
"""

from dataclasses import dataclass
from typing import Optional

from src.back.l01_domain.army.constants import EXHAUSTION_THRESHOLD_STAMINA
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import (
    BATTLE_MAP_DIMENSIONS,
    TerrainType,
)
from src.back.l01_domain.combat.models.effects import TerrainProfile
from src.back.l01_domain.combat.models.state import (
    SquadOrder,
    TacticalBattleState,
    TacticalCellState,
)
from src.back.l01_domain.combat.models.reports import MovementActionReport
from src.back.l01_domain.maps.models.tactical import (
    CellCoordinates,
    cell_line,
    is_within_bounds,
)


@dataclass
class _PathWalkResult:
    """Итог попытки провести отряд по рассчитанной траектории."""

    path_taken: list[CellCoordinates]
    last_valid_pos: CellCoordinates
    was_blocked: bool = False
    is_formation_broken: bool = False
    total_stamina_spent: float = 0.0


class TacticalMovementService:
    """
    Оркестрирует перемещение отрядов по тактической сетке с учетом темпа,
    препятствий, рельефа, блокировок и панического отступления.
    """

    def process_movement(
        self,
        battle_state: TacticalBattleState,
        squads: dict[str, Squad],
        ordered_squad_ids: list[str],
        terrain_profiles: Optional[dict[TerrainType, TerrainProfile]] = None,
    ) -> list[MovementActionReport]:
        """
        Выполняет перемещение всех отрядов в порядке очередности инициативы.
        """

        profiles = terrain_profiles or {}
        reports: list[MovementActionReport] = []

        map_width, map_height = BATTLE_MAP_DIMENSIONS.get(battle_state.map_size, (17, 17))
        orders_by_squad = {order.squad_id: order for order in battle_state.pending_orders}
        cell_map = self._build_cell_map(battle_state)
        squad_positions = self._build_squad_position_index(battle_state)

        for squad_id in ordered_squad_ids:
            squad = squads.get(squad_id)
            if squad is None or squad.state.unit_count <= 0:
                continue

            current_pos = squad_positions.get(squad_id)
            if current_pos is None:
                continue

            order = orders_by_squad.get(squad_id)
            is_fleeing = squad.state.is_in_panic

            target_cell, pace = self._resolve_target_and_pace(
                squad_id=squad_id,
                current_pos=current_pos,
                order=order,
                is_fleeing=is_fleeing,
                battle_state=battle_state,
                map_width=map_width,
            )

            # Оборона на месте: нулевой темп или цель совпадает с текущей клеткой
            if pace == 0.0 or target_cell == current_pos:
                reports.append(
                    self._build_stationary_report(squad_id, current_pos, is_fleeing)
                )
                continue

            full_line = cell_line(current_pos, target_cell)
            if len(full_line) <= 1:
                continue

            # Исключаем стартовую клетку из шагов
            max_steps = self._max_movement_steps(squad, pace)
            steps_to_check = full_line[1:][:max_steps]

            walk_result = self._walk_path(
                squad=squad,
                squad_id=squad_id,
                start_pos=current_pos,
                steps=steps_to_check,
                pace=pace,
                cell_map=cell_map,
                profiles=profiles,
                map_width=map_width,
                map_height=map_height,
            )

            squad_positions[squad_id] = walk_result.last_valid_pos
            self._apply_stamina_and_exhaustion(squad, walk_result.total_stamina_spent)

            reports.append(
                MovementActionReport(
                    squad_id=squad_id,
                    start_cell=current_pos,
                    end_cell=walk_result.last_valid_pos,
                    path_taken=walk_result.path_taken,
                    stamina_spent=walk_result.total_stamina_spent,
                    is_formation_broken=walk_result.is_formation_broken,
                    was_blocked=walk_result.was_blocked,
                    is_fleeing=is_fleeing,
                )
            )

        return reports

    def _build_cell_map(
        self, battle_state: TacticalBattleState
    ) -> dict[tuple[int, int], TacticalCellState]:
        """Карта размещения клеток сетки {coordinates: cell_state}."""
        return {cell.coordinates.to_tuple(): cell for cell in battle_state.cells}

    def _build_squad_position_index(
        self, battle_state: TacticalBattleState
    ) -> dict[str, CellCoordinates]:
        """Обратное отображение {squad_id: current_cell_coordinates}."""
        squad_positions: dict[str, CellCoordinates] = {}
        for cell in battle_state.cells:
            if cell.occupant_squad_id is not None:
                squad_positions[cell.occupant_squad_id] = cell.coordinates
        return squad_positions

    def _resolve_target_and_pace(
        self,
        squad_id: str,
        current_pos: CellCoordinates,
        order: Optional[SquadOrder],
        is_fleeing: bool,
        battle_state: TacticalBattleState,
        map_width: int,
    ) -> tuple[CellCoordinates, float]:
        """
        Определяет целевую клетку и темп движения отряда на этот раунд:
        паническое бегство к границе своей стороны, приказ игрока, либо
        удержание позиции при отсутствии приказа.
        """
        if is_fleeing:
            is_attacker = squad_id in battle_state.attacker_squad_ids
            target_x = 0 if is_attacker else map_width - 1
            return CellCoordinates(x=target_x, y=current_pos.y), 1.0

        if order is not None:
            return order.target_cell, order.pace

        return current_pos, 0.0

    def _build_stationary_report(
        self, squad_id: str, current_pos: CellCoordinates, is_fleeing: bool
    ) -> MovementActionReport:
        """Отчет об отряде, оставшемся на месте (оборона либо цель уже достигнута)."""
        return MovementActionReport(
            squad_id=squad_id,
            start_cell=current_pos,
            end_cell=current_pos,
            path_taken=[current_pos],
            stamina_spent=0.0,
            is_formation_broken=False,
            was_blocked=False,
            is_fleeing=is_fleeing,
        )

    def _max_movement_steps(self, squad: Squad, pace: float) -> int:
        """Максимальная дальность перемещения в клетках при данном темпе."""
        base_speed = squad.total_effective_speed * pace
        return max(1, int(round(base_speed)))

    def _step_stamina_cost(self, squad: Squad, pace: float) -> float:
        """Расход выносливости за один шаг с учетом темпа и снаряжения."""
        cost = 2.0 * pace
        if squad.armor is not None:
            cost += squad.armor.stats.stamina_drain_per_turn
        if squad.weapon is not None:
            cost += squad.weapon.stats.stamina_drain_per_turn
        return cost

    def _evaluate_terrain(
        self,
        cell_state: TacticalCellState,
        profiles: dict[TerrainType, TerrainProfile],
    ) -> tuple[bool, bool]:
        """
        Оценивает клетку по профилю местности.
        Возвращает (клетка_непроходима, ломает_строй).
        """
        profile = profiles.get(cell_state.terrain_type)
        if profile is None:
            return False, False

        is_impassable = profile.movement_speed_modifier <= 0.0
        return is_impassable, profile.breaks_formation

    def _walk_path(
        self,
        squad: Squad,
        squad_id: str,
        start_pos: CellCoordinates,
        steps: list[CellCoordinates],
        pace: float,
        cell_map: dict[tuple[int, int], TacticalCellState],
        profiles: dict[TerrainType, TerrainProfile],
        map_width: int,
        map_height: int,
    ) -> _PathWalkResult:
        """
        Проводит отряд по рассчитанной траектории шаг за шагом, останавливаясь
        на первом препятствии: границе карты, занятой клетке или непроходимой
        местности. Списывает выносливость за каждый успешно пройденный шаг
        и переносит занятость клеток на сетке.
        """
        result = _PathWalkResult(path_taken=[start_pos], last_valid_pos=start_pos)

        for next_cell in steps:
            if not is_within_bounds(next_cell, map_width, map_height):
                result.was_blocked = True
                break

            target_cell_state = cell_map.get(next_cell.to_tuple())
            if target_cell_state is None:
                result.was_blocked = True
                break

            if (
                target_cell_state.occupant_squad_id is not None
                and target_cell_state.occupant_squad_id != squad_id
            ):
                result.was_blocked = True
                break

            is_impassable, breaks_formation = self._evaluate_terrain(
                target_cell_state, profiles
            )
            if breaks_formation:
                result.is_formation_broken = True
            if is_impassable:
                result.was_blocked = True
                break

            result.total_stamina_spent += self._step_stamina_cost(squad, pace)

            old_cell_state = cell_map.get(result.last_valid_pos.to_tuple())
            if old_cell_state is not None and old_cell_state.occupant_squad_id == squad_id:
                old_cell_state.occupant_squad_id = None

            target_cell_state.occupant_squad_id = squad_id
            result.last_valid_pos = next_cell
            result.path_taken.append(next_cell)

        return result

    def _apply_stamina_and_exhaustion(self, squad: Squad, stamina_spent: float) -> None:
        """Списывает потраченную выносливость и фиксирует истощение отряда."""
        squad.state.stamina = max(0.0, squad.state.stamina - stamina_spent)
        if squad.state.stamina <= EXHAUSTION_THRESHOLD_STAMINA:
            squad.state.is_exhausted = True
