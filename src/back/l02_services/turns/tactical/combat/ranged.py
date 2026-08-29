"""
Сервис разрешения дистанционных атак.
(луки, арбалеты, аркебузы, магия и т.п.)
"""

from typing import Optional

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import (
    MELEE_LONG_RANGE_CELLS,
    TerrainType,
    WeatherCondition,
)
from src.back.l01_domain.army.constants import EquipmentTag
from src.back.l01_domain.combat.models.effects import TerrainProfile
from src.back.l01_domain.combat.models.reports import RangedCombatReport
from src.back.l01_domain.combat.models.state import TacticalBattleState, TacticalCellState
from src.back.l01_domain.combat.visibility import resolve_visibility_range_cells
from src.back.l01_domain.maps.models.tactical import (
    CellCoordinates,
    cell_distance_chebyshev,
    cell_line,
)


class TacticalRangedService:
    """
    Выполняет проверки видимости алгоритмом Брезенхэма, расчет укрытий,
    погодных условий, дружественного огня и наносит дистанционный урон.

    Дальность оружия - это не то же самое, что дальность стрельбы: ночью и
    в пепельной буре отряд просто не различает цель, докуда бы ни добивал
    его лук.
    """

    def resolve_ranged_attacks(
        self,
        battle_state: TacticalBattleState,
        squads: dict[str, Squad],
        terrain_profiles: Optional[dict[TerrainType, TerrainProfile]] = None,
    ) -> list[RangedCombatReport]:
        """
        Разрешает все дистанционные приказы стрельбы.
        """

        profiles = terrain_profiles or {}
        reports: list[RangedCombatReport] = []

        # Предел видимости на поле общий для всех: он задается временем суток
        # и погодой боя, а не снаряжением конкретного отряда
        visibility_range = resolve_visibility_range_cells(
            battle_state.time_of_day, battle_state.weather
        )

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

            # Тип оружия отряда
            weapon_range = (
                attacker.weapon.stats.range_hexes if attacker.weapon is not None else 1
            )
            if weapon_range <= MELEE_LONG_RANGE_CELLS:
                continue

            # Позиция отряда
            attacker_pos = squad_positions.get(order.squad_id)
            if attacker_pos is None:
                continue

            # Дистанция до целевого отряда
            distance = cell_distance_chebyshev(attacker_pos, order.target_cell)
            if distance > weapon_range or distance <= 1:
                continue

            # =======================================================================
            # Проверка предела видимости: во тьму и в бурю не стреляют
            # =======================================================================

            if distance > visibility_range:
                reports.append(
                    RangedCombatReport(
                        attacker_squad_id=order.squad_id,
                        target_cell=order.target_cell,
                        is_out_of_sight=True,
                    )
                )
                continue

            # =======================================================================
            # Проверка погоды: дождь дает осечки пороховому оружию
            # =======================================================================

            if (
                battle_state.weather == WeatherCondition.HEAVY_RAIN
                and attacker.weapon is not None
                and attacker.weapon.has_tag(EquipmentTag.BLACKPOWDER)
            ):
                reports.append(
                    RangedCombatReport(
                        attacker_squad_id=order.squad_id,
                        target_cell=order.target_cell,
                        is_misfire=True,
                    )
                )
                continue

            # =======================================================================
            # Трассировка линии видимости
            # =======================================================================

            line = cell_line(attacker_pos, order.target_cell)
            has_obstacle = False
            friendly_fire_squad_id = None

            for intermediate_cell in line[1:-1]:
                cell_state = cell_map.get(intermediate_cell.to_tuple())
                if cell_state is None:
                    continue

                if cell_state.terrain_type in (TerrainType.MOUNTAIN, TerrainType.RUINS):
                    has_obstacle = True
                    break

                if cell_state.occupant_squad_id is not None:
                    friendly_fire_squad_id = cell_state.occupant_squad_id
                    break

            if has_obstacle:
                continue

            target_cell_state = cell_map.get(order.target_cell.to_tuple())
            target_squad_id = (
                target_cell_state.occupant_squad_id if target_cell_state else None
            )

            effective_target_id = friendly_fire_squad_id or target_squad_id
            if effective_target_id is None:
                continue

            # Целевой отряд для атаки
            target_squad = squads.get(effective_target_id)
            if target_squad is None or target_squad.state.unit_count <= 0:
                continue

            # Целевая клетка для атаки
            target_cell = squad_positions.get(effective_target_id, order.target_cell)
            target_profile = profiles.get(
                cell_map.get(
                    target_cell.to_tuple(),
                    TacticalCellState(coordinates=target_cell),
                ).terrain_type,
                TerrainProfile(terrain_type=TerrainType.PLAIN),
            )

            # Укрытия от стрельбы у целевого отряда для атаки
            cover_reduction = 0.35 if target_profile.provides_ranged_cover else 0.0
            total_raw_damage = (
                attacker.total_attack_damage
                * attacker.state.unit_count
                * (1.0 - cover_reduction)
            )

            ap = attacker.weapon.stats.armor_piercing if attacker.weapon else 0.0
            kills = target_squad.take_damage(total_raw_damage, armor_piercing=ap)

            reports.append(
                RangedCombatReport(
                    attacker_squad_id=order.squad_id,
                    target_cell=order.target_cell,
                    target_squad_id=target_squad_id,
                    damage_dealt=total_raw_damage,
                    kills=kills,
                    is_misfire=False,
                    friendly_fire_kills=kills if friendly_fire_squad_id else 0,
                    friendly_fire_squad_id=friendly_fire_squad_id,
                    cover_reduction=cover_reduction,
                )
            )

        return reports
