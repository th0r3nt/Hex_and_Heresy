"""
Сервис поклеточного перемещения отрядов, учета ландшафта,
коллизий, расхода выносливости и маршрутов бегства.
"""

from typing import Optional

from src.back.l01_domain.army.constants import EXHAUSTION_THRESHOLD_STAMINA
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import (
    BATTLE_MAP_DIMENSIONS,
    TerrainType,
)
from src.back.l01_domain.combat.models.effects import TerrainProfile
from src.back.l01_domain.combat.models.state import (
    TacticalBattleState,
    TacticalCellState,
)
from src.back.l01_domain.combat.models.reports import MovementActionReport
from src.back.l01_domain.maps.models.tactical import (
    CellCoordinates,
    cell_line,
    is_within_bounds,
)

class TacticalMovementService:
    """
    Оркестрирует перемещение отрядов по тактической сетке с учетом темпа,
    препятствий, рельефа, блокировок и панического отступления.
    """

    # TODO: распилить на функции
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

        map_dimensions = BATTLE_MAP_DIMENSIONS.get(battle_state.map_size, (17, 17))
        map_width, map_height = map_dimensions

        orders_by_squad = {order.squad_id: order for order in battle_state.pending_orders}

        # ===================================================
        # Карта размещения отрядов на сетке {coordinates: cell_state}
        # ===================================================

        cell_map: dict[tuple[int, int], TacticalCellState] = {
            cell.coordinates.to_tuple(): cell for cell in battle_state.cells
        }

        # ===================================================
        # Обратное отображение {squad_id: current_cell_coordinates}
        # ===================================================

        squad_positions: dict[str, CellCoordinates] = {}
        for cell in battle_state.cells:
            if cell.occupant_squad_id is not None:
                squad_positions[cell.occupant_squad_id] = cell.coordinates

        for squad_id in ordered_squad_ids:
            squad = squads.get(squad_id)
            if squad is None or squad.state.unit_count <= 0:
                continue

            current_pos = squad_positions.get(squad_id)
            if current_pos is None:
                continue

            order = orders_by_squad.get(squad_id)
            is_fleeing = squad.state.is_in_panic

            # ===================================================
            # Определение целевой точки
            # ===================================================

            if is_fleeing:
                # Паникующие отряды бегут к границе своей стороны
                is_attacker = squad_id in battle_state.attacker_squad_ids
                target_x = 0 if is_attacker else map_width - 1
                target_cell = CellCoordinates(x=target_x, y=current_pos.y)
                pace = 1.0
            elif order is not None:
                target_cell = order.target_cell
                pace = order.pace
            else:
                # Нет приказа — отряд удерживает позицию
                target_cell = current_pos
                pace = 0.0

            # ===================================================
            # При нулевом темпе (оборона) отряд остается на месте
            # ===================================================

            if pace == 0.0 or target_cell == current_pos:
                reports.append(
                    MovementActionReport(
                        squad_id=squad_id,
                        start_cell=current_pos,
                        end_cell=current_pos,
                        path_taken=[current_pos],
                        stamina_spent=0.0,
                        is_formation_broken=False,
                        was_blocked=False,
                        is_fleeing=is_fleeing,
                    )
                )
                continue

            # ===================================================
            # Расчет максимальной дальности перемещения в клетках
            # ===================================================

            base_speed = squad.total_effective_speed * pace
            max_steps = max(1, int(round(base_speed)))

            # ===================================================
            # Построение полной траектории алгоритмом Брезенхэма
            # ===================================================

            full_line = cell_line(current_pos, target_cell)
            if len(full_line) <= 1:
                continue

            # Исключаем стартовую клетку из шагов
            potential_steps = full_line[1:]
            actual_steps_to_check = potential_steps[:max_steps]

            path_taken: list[CellCoordinates] = [current_pos]
            last_valid_pos = current_pos
            was_blocked = False
            is_formation_broken = False
            total_stamina_spent = 0.0

            # ===================================================
            # Цикл перемещения к целевой клетке
            # ===================================================

            for next_cell in actual_steps_to_check:
                # Проверка границ поля боя
                if not is_within_bounds(next_cell, map_width, map_height):
                    was_blocked = True
                    break

                target_cell_state = cell_map.get(next_cell.to_tuple())
                if target_cell_state is None:
                    was_blocked = True
                    break

                # ===================================================
                # Проверка занятости клетки другим отрядом (коллизия)
                # ===================================================

                if (
                    target_cell_state.occupant_squad_id is not None
                    and target_cell_state.occupant_squad_id != squad_id
                ):
                    was_blocked = True
                    break

                # ===================================================
                # Проверка влияния профиля местности
                # ===================================================

                cell_terrain = target_cell_state.terrain_type
                profile = profiles.get(cell_terrain)

                if profile is not None:
                    if profile.breaks_formation:
                        is_formation_broken = True

                    # Если местность непроходима (множитель скорости == 0)
                    if profile.movement_speed_modifier <= 0.0:
                        was_blocked = True
                        break

                # ===================================================
                # Списание выносливости за каждый шаг
                # ===================================================

                step_stamina_cost = 2.0 * pace
                if squad.armor is not None:
                    step_stamina_cost += squad.armor.stats.stamina_drain_per_turn
                if squad.weapon is not None:
                    step_stamina_cost += squad.weapon.stats.stamina_drain_per_turn

                total_stamina_spent += step_stamina_cost

                # ===================================================
                # Освобождаем предыдущую клетку и занимаем новую
                # ===================================================

                old_cell_state = cell_map.get(last_valid_pos.to_tuple())
                if old_cell_state is not None and old_cell_state.occupant_squad_id == squad_id:
                    old_cell_state.occupant_squad_id = None

                target_cell_state.occupant_squad_id = squad_id
                last_valid_pos = next_cell
                path_taken.append(next_cell)

            # ===================================================
            # Обновляем позицию в локальном реестре
            # ===================================================

            squad_positions[squad_id] = last_valid_pos

            # ===================================================
            # Списываем выносливость и проверяем истощение
            # ===================================================

            squad.state.stamina = max(0.0, squad.state.stamina - total_stamina_spent)
            if squad.state.stamina <= EXHAUSTION_THRESHOLD_STAMINA:
                squad.state.is_exhausted = True

            reports.append(
                MovementActionReport(
                    squad_id=squad_id,
                    start_cell=current_pos,
                    end_cell=last_valid_pos,
                    path_taken=path_taken,
                    stamina_spent=total_stamina_spent,
                    is_formation_broken=is_formation_broken,
                    was_blocked=was_blocked,
                    is_fleeing=is_fleeing,
                )
            )

        return reports
