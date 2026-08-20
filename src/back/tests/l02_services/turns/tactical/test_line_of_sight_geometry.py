"""
Тесты линии прямой видимости (Line of Sight), перекрытия препятствиями,
дружественного огня (Friendly Fire) и снижения урона в укрытиях.
"""

import pytest

from src.back.l01_domain.army.constants import (
    EquipmentSlot,
    EquipmentTag,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import TerrainType
from src.back.l01_domain.combat.models.effects import TerrainProfile
from src.back.l01_domain.combat.models.state import SquadOrder
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l02_services.turns.tactical.combat.ranged import TacticalRangedService
from src.back.tests.l02_services.turns.tactical.conftest import place_squad_on_grid


@pytest.fixture
def longbow() -> Equipment:
    return Equipment(
        id="wpn_longbow_test",
        name="Длинный лук",
        lore="...",
        slot=EquipmentSlot.WEAPON,
        category=WeaponCategory.BOW,
        tags={EquipmentTag.STRING_BASED, EquipmentTag.TWO_HANDED},
        tier=2,
        stats=EquipmentStats(damage=10.0, range_hexes=8),
    )


class TestRangedLineOfSightAndObstacles:
    def test_obstacle_in_middle_completely_blocks_shot(
        self, empty_battle_state, archetype_human_sword, longbow
    ):
        sq_archer = Squad.create_new(archetype=archetype_human_sword, weapon=longbow)
        sq_archer.id = "archers"
        sq_target = Squad.create_new(archetype=archetype_human_sword)
        sq_target.id = "target"
        squads = {"archers": sq_archer, "target": sq_target}

        # Стрелок на (0, 0), цель на (6, 0), гора на (3, 0)
        place_squad_on_grid(empty_battle_state, "archers", 0, 0)
        place_squad_on_grid(empty_battle_state, "target", 6, 0)

        for cell in empty_battle_state.cells:
            if cell.coordinates.to_tuple() == (3, 0):
                cell.terrain_type = TerrainType.MOUNTAIN
                break

        empty_battle_state.queue_order(
            SquadOrder(squad_id="archers", target_cell=CellCoordinates(x=6, y=0))
        )

        service = TacticalRangedService()
        reports = service.resolve_ranged_attacks(empty_battle_state, squads)

        # Выстрел не состоялся из-за отсутствия прямой видимости
        assert len(reports) == 0
        assert sq_target.state.unit_count == 100

    def test_ruins_block_diagonal_shot(
        self, empty_battle_state, archetype_human_sword, longbow
    ):
        sq_archer = Squad.create_new(archetype=archetype_human_sword, weapon=longbow)
        sq_archer.id = "archers"
        sq_target = Squad.create_new(archetype=archetype_human_sword)
        sq_target.id = "target"
        squads = {"archers": sq_archer, "target": sq_target}

        # Диагональный выстрел из (1, 1) в (5, 5) через руины в (3, 3)
        place_squad_on_grid(empty_battle_state, "archers", 1, 1)
        place_squad_on_grid(empty_battle_state, "target", 5, 5)

        for cell in empty_battle_state.cells:
            if cell.coordinates.to_tuple() == (3, 3):
                cell.terrain_type = TerrainType.RUINS
                break

        empty_battle_state.queue_order(
            SquadOrder(squad_id="archers", target_cell=CellCoordinates(x=5, y=5))
        )

        service = TacticalRangedService()
        reports = service.resolve_ranged_attacks(empty_battle_state, squads)

        assert len(reports) == 0
        assert sq_target.state.unit_count == 100


class TestFriendlyFireAndCoverGeometry:
    def test_friendly_unit_on_trajectory_intercepts_full_damage(
        self, empty_battle_state, archetype_human_sword, longbow
    ):
        sq_archer = Squad.create_new(archetype=archetype_human_sword, weapon=longbow)
        sq_archer.id = "archers"
        sq_meatshield = Squad.create_new(archetype=archetype_human_sword)
        sq_meatshield.id = "allied_infantry"
        sq_target = Squad.create_new(archetype=archetype_human_sword)
        sq_target.id = "target"
        squads = {
            "archers": sq_archer,
            "allied_infantry": sq_meatshield,
            "target": sq_target,
        }

        # Союзник стоит на (3, 0) прямо между лучником (0, 0) и врагом (6, 0)
        place_squad_on_grid(empty_battle_state, "archers", 0, 0)
        place_squad_on_grid(empty_battle_state, "allied_infantry", 3, 0)
        place_squad_on_grid(empty_battle_state, "target", 6, 0)

        empty_battle_state.queue_order(
            SquadOrder(squad_id="archers", target_cell=CellCoordinates(x=6, y=0))
        )

        service = TacticalRangedService()
        reports = service.resolve_ranged_attacks(empty_battle_state, squads)

        assert len(reports) == 1
        report = reports[0]
        assert report.friendly_fire_squad_id == "allied_infantry"
        assert report.friendly_fire_kills > 0
        assert sq_meatshield.state.unit_count < 100
        # Враг не получил повреждений
        assert sq_target.state.unit_count == 100

    def test_forest_cover_reduces_ranged_damage_by_35_percent(
        self, empty_battle_state, archetype_human_sword, longbow
    ):
        sq_archer = Squad.create_new(archetype=archetype_human_sword, weapon=longbow)
        sq_archer.id = "archers"
        sq_target = Squad.create_new(archetype=archetype_human_sword)
        sq_target.id = "target"
        squads = {"archers": sq_archer, "target": sq_target}

        place_squad_on_grid(empty_battle_state, "archers", 0, 0)
        place_squad_on_grid(empty_battle_state, "target", 4, 0)

        for cell in empty_battle_state.cells:
            if cell.coordinates.to_tuple() == (4, 0):
                cell.terrain_type = TerrainType.FOREST
                break

        profiles = {
            TerrainType.FOREST: TerrainProfile(
                terrain_type=TerrainType.FOREST, provides_ranged_cover=True
            )
        }

        empty_battle_state.queue_order(
            SquadOrder(squad_id="archers", target_cell=CellCoordinates(x=4, y=0))
        )

        service = TacticalRangedService()
        reports = service.resolve_ranged_attacks(
            empty_battle_state, squads, terrain_profiles=profiles
        )

        assert len(reports) == 1
        report = reports[0]
        assert report.cover_reduction == 0.35
        # Базовый сырой урон = 10 (урон лука) * 100 (бойцов) * 0.65 = 650.0
        assert report.damage_dealt == pytest.approx(650.0)