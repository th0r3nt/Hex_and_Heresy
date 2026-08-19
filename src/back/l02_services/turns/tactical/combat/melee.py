"""
Сервис разрешения рукопашных схваток с учетом направлений атак и бронепробития.
"""

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import MELEE_LONG_RANGE_CELLS
from src.back.l01_domain.combat.models.reports import MeleeCombatReport
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.maps.models.tactical import CellCoordinates, cell_distance_chebyshev


class TacticalMeleeService:
    """
    Разрешает рукопашный бой смежных отрядов, рассчитывает угол атаки
    (лоб, фланг — срез 50% брони, тыл — срез 100% брони) и наносит урон.
    """

    def resolve_melee_clashes(
        self,
        battle_state: TacticalBattleState,
        squads: dict[str, Squad],
    ) -> list[MeleeCombatReport]:
        """
        Разрешает все рукопашные атаки раунда.
        """

        reports: list[MeleeCombatReport] = []

        cell_map = {cell.coordinates.to_tuple(): cell for cell in battle_state.cells}
        squad_positions: dict[str, CellCoordinates] = {
            cell.occupant_squad_id: cell.coordinates
            for cell in battle_state.cells
            if cell.occupant_squad_id is not None
        }

        for order in battle_state.pending_orders:
            # =======================================================================
            # Проверки на валидность
            # =======================================================================

            # Количество юнитов в отряде
            attacker = squads.get(order.squad_id)
            if attacker is None or attacker.state.unit_count <= 0:
                continue

            # Позиция отряда
            attacker_pos = squad_positions.get(order.squad_id)
            if attacker_pos is None:
                continue

            # Дистанция от атакуещего до защищающегося
            distance = cell_distance_chebyshev(attacker_pos, order.target_cell)
            if distance > MELEE_LONG_RANGE_CELLS:
                continue

            # Целевая клетка для атаки
            target_cell_state = cell_map.get(order.target_cell.to_tuple())
            if target_cell_state is None or target_cell_state.occupant_squad_id is None:
                continue

            # Защищающийся отряд
            defender_id = target_cell_state.occupant_squad_id
            defender = squads.get(defender_id)
            if defender is None or defender.state.unit_count <= 0:
                continue

            # =======================================================================
            # Исключаем атаки по союзникам
            # =======================================================================

            is_attacker_side = order.squad_id in battle_state.attacker_squad_ids
            is_defender_side = defender_id in battle_state.attacker_squad_ids
            if is_attacker_side == is_defender_side:
                continue

            # =======================================================================
            # Определение ориентации защитника и угла атаки
            # =======================================================================

            defender_facing_dx = 1 if defender_id in battle_state.attacker_squad_ids else -1
            attack_dx = target_cell_state.coordinates.x - attacker_pos.x

            if attack_dx == defender_facing_dx:
                flank_angle = "rear"  # TODO: типизировать
                extra_ap = defender.total_effective_armor
                morale_penalty = 15.0
            elif attack_dx == 0:
                flank_angle = "flank"
                extra_ap = defender.total_effective_armor * 0.5
                morale_penalty = 5.0
            else:
                flank_angle = "front"
                extra_ap = 0.0
                morale_penalty = 0.0

            # =======================================================================
            # Подсчет урона и убитых
            # =======================================================================

            base_dmg = attacker.total_attack_damage_vs(defender.size_category)
            total_raw_damage = base_dmg * attacker.state.unit_count

            ap = (attacker.weapon.stats.armor_piercing if attacker.weapon else 0.0) + extra_ap
            kills = defender.take_damage(total_raw_damage, armor_piercing=ap)

            if morale_penalty > 0.0:
                defender.apply_morale_shock(morale_penalty)

            reports.append(
                MeleeCombatReport(
                    attacker_squad_id=order.squad_id,
                    defender_squad_id=defender_id,
                    damage_dealt=total_raw_damage,
                    kills=kills,
                    flank_angle=flank_angle,
                )
            )

        return reports
