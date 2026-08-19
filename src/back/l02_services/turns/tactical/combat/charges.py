"""
Сервис разрешения столкновений фазы натиска и встречных реакций.
"""

from typing import Optional

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import (
    SPEED_CHARGE_PACE,
    ReactionType,
    SurfaceIncline,
    TerrainType,
)
from src.back.l01_domain.combat.models.effects import TerrainProfile
from src.back.l01_domain.combat.models.reports import ChargeStepReport
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.combat.resolution import resolve_charge_reaction
from src.back.l01_domain.maps.models.tactical import CellCoordinates


class TacticalChargeService:
    """
    Выявляет отряды в режиме натиска и рассчитывает встречный урон
    в соответствии с выбранной защитником реакцией.
    """

    def resolve_charges(
        self,
        battle_state: TacticalBattleState,
        squads: dict[str, Squad],
        terrain_profiles: Optional[dict[TerrainType, TerrainProfile]] = None,
    ) -> list[ChargeStepReport]:
        """
        Разрешает все объявленные атаки с темпом натиска (x2.0).
        """

        profiles = terrain_profiles or {}
        reports: list[ChargeStepReport] = []

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

            if order.pace != SPEED_CHARGE_PACE:
                continue

            # Количество юнитов в отряде
            attacker = squads.get(order.squad_id)
            if attacker is None or attacker.state.unit_count <= 0:
                continue

            # Позиция отряда
            attacker_pos = squad_positions.get(order.squad_id)
            if attacker_pos is None:
                continue

            # Целевая клетка натиска
            target_cell_state = cell_map.get(order.target_cell.to_tuple())
            if target_cell_state is None or target_cell_state.occupant_squad_id is None:
                continue

            # Защитник от натиска
            defender_id = target_cell_state.occupant_squad_id
            defender = squads.get(defender_id)
            if defender is None or defender.state.unit_count <= 0:
                continue

            # =======================================================================
            # Исключаем атаки по союзным отрядам
            # =======================================================================

            is_attacker_side = order.squad_id in battle_state.attacker_squad_ids
            is_defender_side = defender_id in battle_state.attacker_squad_ids
            if is_attacker_side == is_defender_side:
                continue

            # =======================================================================
            # Определение реакции защитника
            # =======================================================================

            defender_order = next(
                (o for o in battle_state.pending_orders if o.squad_id == defender_id),
                None,
            )
            reaction = (
                defender_order.reaction
                if defender_order and defender_order.reaction
                else ReactionType.ACCEPT_CHARGE
            )

            attacker_cell_state = cell_map.get(attacker_pos.to_tuple())
            attacker_terrain = (
                profiles.get(
                    attacker_cell_state.terrain_type,
                    TerrainProfile(terrain_type=TerrainType.PLAIN),
                )
                if attacker_cell_state
                else TerrainProfile(terrain_type=TerrainType.PLAIN)
            )
            defender_terrain = profiles.get(
                target_cell_state.terrain_type,
                TerrainProfile(terrain_type=TerrainType.PLAIN),
            )

            # =======================================================================
            # Математический расчет столкновения
            # =======================================================================

            charge_res = resolve_charge_reaction(
                attacker=attacker,
                defender=defender,
                reaction=reaction,
                attacker_terrain=attacker_terrain,
                defender_terrain=defender_terrain,
                elevation=SurfaceIncline.FLAT,
            )

            # =======================================================================
            # Нанесение урона и списание бойцов защитника
            # =======================================================================

            attacker_deaths = attacker.take_damage(charge_res.damage_to_attacker)
            defender_deaths = defender.take_damage(charge_res.damage_to_defender)

            if charge_res.defender_morale_shock > 0:
                defender.apply_morale_shock(charge_res.defender_morale_shock)

            reports.append(
                ChargeStepReport(
                    attacker_squad_id=order.squad_id,
                    defender_squad_id=defender_id,
                    reaction=reaction,
                    damage_to_attacker=charge_res.damage_to_attacker,
                    damage_to_defender=charge_res.damage_to_defender,
                    attacker_deaths=attacker_deaths,
                    defender_deaths=defender_deaths,
                    defender_morale_shock=charge_res.defender_morale_shock,
                )
            )

        return reports
