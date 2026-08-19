"""
Сервис расчета психологии отрядов, цепной паники, гор трупов и ветеранства.
"""

from src.back.l01_domain.army.constants import PANIC_THRESHOLD_MORALE
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import CORPSE_PILE_UNIT_THRESHOLD, TerrainType
from src.back.l01_domain.combat.models.reports import MoraleAndEnvironmentReport
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.combat.resolution import calculate_effective_corpse_weight
from src.back.l01_domain.maps.models.tactical import CellCoordinates, cell_neighbors


class TacticalMoraleEnvironmentService:
    """
    Отслеживает тяжелые потери, инициирует панику и цепной шок соседей,
    аккумулирует вес тел на клетках и выявляет кандидатов в ветераны.
    """

    def __init__(self) -> None:
        self._accumulated_corpse_weights: dict[tuple[int, int], float] = {}

    def reset_accumulators(self) -> None:
        """
        Очищает накопитель веса трупов при старте нового сражения.
        """
        self._accumulated_corpse_weights.clear()

    def process_morale_and_environment(
        self,
        battle_state: TacticalBattleState,
        squads: dict[str, Squad],
        all_deaths_by_squad: dict[str, int],
        all_kills_by_squad: dict[str, int],
    ) -> MoraleAndEnvironmentReport:
        """
        Проводит психологический аудит и проверяет трансформацию окружения.
        """

        panicking_squad_ids: list[str] = []
        chain_panic_shocks: dict[str, float] = {}
        new_corpse_piles: list[CellCoordinates] = []
        veterancy_candidate_ids: list[str] = []

        squad_positions: dict[str, CellCoordinates] = {
            cell.occupant_squad_id: cell.coordinates
            for cell in battle_state.cells
            if cell.occupant_squad_id is not None
        }

        # =======================================================================
        # Проверка потерь и паники
        # =======================================================================

        for squad_id, squad in squads.items():
            if squad.state.unit_count <= 0:
                continue

            deaths = all_deaths_by_squad.get(squad_id, 0)
            initial_count = squad.state.unit_count + deaths

            if initial_count > 0 and (deaths / initial_count) >= 0.25:
                squad.apply_morale_shock(15.0)

            if squad.state.morale <= PANIC_THRESHOLD_MORALE and not squad.state.is_in_panic:
                squad.state.is_in_panic = True
                panicking_squad_ids.append(squad_id)

                current_pos = squad_positions.get(squad_id)

                if current_pos is not None:
                    neighbor_coords = cell_neighbors(current_pos, include_diagonals=True)

                    for n_coord in neighbor_coords:
                        n_cell = next(
                            (c for c in battle_state.cells if c.coordinates == n_coord),
                            None,
                        )
                        if n_cell and n_cell.occupant_squad_id:
                            neighbor_id = n_cell.occupant_squad_id
                            is_attacker_side = squad_id in battle_state.attacker_squad_ids
                            is_neighbor_attacker = (
                                neighbor_id in battle_state.attacker_squad_ids
                            )
                            if is_attacker_side == is_neighbor_attacker:
                                neighbor_squad = squads.get(neighbor_id)
                                if neighbor_squad and neighbor_squad.state.unit_count > 0:
                                    neighbor_squad.apply_morale_shock(10.0)
                                    chain_panic_shocks[neighbor_id] = 10.0

        # =======================================================================
        # Аккумуляция гор трупов
        # =======================================================================

        for squad_id, deaths in all_deaths_by_squad.items():
            if deaths <= 0:
                continue
            squad = squads.get(squad_id)
            if squad is None:
                continue

            pos = squad_positions.get(squad_id)
            if pos is None:
                continue

            weight = calculate_effective_corpse_weight(deaths, squad.size_category)
            coord_key = pos.to_tuple()
            current_weight = self._accumulated_corpse_weights.get(coord_key, 0.0) + weight
            self._accumulated_corpse_weights[coord_key] = current_weight

            if current_weight >= CORPSE_PILE_UNIT_THRESHOLD:
                target_cell = next(
                    (c for c in battle_state.cells if c.coordinates == pos), None
                )
                if (
                    target_cell is not None
                    and target_cell.terrain_type != TerrainType.CORPSE_PILE
                ):
                    target_cell.terrain_type = TerrainType.CORPSE_PILE
                    new_corpse_piles.append(pos)

        # =======================================================================
        # Фиксация подвигов ветеранства
        # =======================================================================

        for squad_id, squad in squads.items():
            if squad.state.unit_count <= 0 or squad.veterancy.is_named:
                continue

            # TODO: слишком примитивно, нужно сделать гибче
            kills = all_kills_by_squad.get(squad_id, 0)
            if kills >= 100:
                veterancy_candidate_ids.append(squad_id)
                continue

            if squad.state.unit_count <= (squad.archetype.default_unit_count * 0.10):
                veterancy_candidate_ids.append(squad_id)

        # =======================================================================
        # Результат
        # =======================================================================

        return MoraleAndEnvironmentReport(
            panicking_squad_ids=panicking_squad_ids,
            chain_panic_shocks=chain_panic_shocks,
            new_corpse_piles=new_corpse_piles,
            veterancy_candidate_ids=veterancy_candidate_ids,
        )
