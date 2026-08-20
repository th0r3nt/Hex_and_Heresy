"""
Тесты краевых случаев математики натиска, встречных ударов и влияния рельефа.
"""

import pytest

from src.back.l01_domain.army.constants import (
    EquipmentSlot,
    EquipmentTag,
    UnitSizeCategory,
    WeaponCategory,
    AccessoryCategory,
)
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.combat.constants import (
    FLEE_CATCH_DAMAGE_MULTIPLIER,
    MORALE_THRESHOLD_ACCEPT_CHARGE,
    ReactionType,
    SurfaceIncline,
    TerrainType,
)
from src.back.l01_domain.combat.models.effects import TerrainProfile
from src.back.l01_domain.combat.resolution import (
    calculate_charge_damage,
    resolve_charge_reaction,
)
from src.back.l01_domain.common import FactionRace


@pytest.fixture
def cavalry_squad() -> Squad:
    archetype = UnitArchetype(
        id="unit_knights",
        race=FactionRace.HUMANS,
        name="Рыцари",
        tier=4,
        default_unit_count=30,
        base_stats=BaseUnitStats(
            max_hp=40.0,
            base_speed=4.0,
            base_morale=80.0,
            base_stamina=100.0,
            size_category=UnitSizeCategory.LARGE,
        ),
    )
    lance = Equipment(
        id="wpn_lance",
        name="Рыцарское копье",
        lore="...",
        slot=EquipmentSlot.WEAPON,
        category=WeaponCategory.SPEAR,
        tags={EquipmentTag.TWO_HANDED},
        tier=4,
        stats=EquipmentStats(damage=20.0),
    )
    return Squad.create_new(archetype=archetype, weapon=lance)


@pytest.fixture
def infantry_squad() -> Squad:
    archetype = UnitArchetype(
        id="unit_spearmen",
        race=FactionRace.HUMANS,
        name="Копейщики",
        tier=1,
        default_unit_count=100,
        base_stats=BaseUnitStats(
            max_hp=15.0,
            base_speed=2.0,
            base_morale=40.0,
            base_stamina=100.0,
            size_category=UnitSizeCategory.MEDIUM,
        ),
    )
    spear = Equipment(
        id="wpn_spear",
        name="Пехотное копье",
        lore="...",
        slot=EquipmentSlot.WEAPON,
        category=WeaponCategory.SPEAR,
        tags={EquipmentTag.TWO_HANDED, EquipmentTag.BRACEABLE},
        tier=1,
        stats=EquipmentStats(damage=6.0),
    )
    return Squad.create_new(archetype=archetype, weapon=spear)


@pytest.fixture
def plain_terrain() -> TerrainProfile:
    return TerrainProfile(terrain_type=TerrainType.PLAIN)


@pytest.fixture
def swamp_terrain() -> TerrainProfile:
    return TerrainProfile(terrain_type=TerrainType.SWAMP, charge_penalty=1.0)


class TestChargeCalculationEdgeCases:
    def test_charge_with_zero_speed_inflicts_zero_damage(
        self, cavalry_squad, infantry_squad, plain_terrain
    ):
        # Обездвиживаем кавалерию
        heavy_weight = Equipment(
            id="acc_stone",
            name="Груз",
            lore="...",
            slot=EquipmentSlot.ACCESSORY,
            category=AccessoryCategory.MISC,
            tier=1,
            stats=EquipmentStats(speed_modifier=-1.0),
        )
        cavalry_squad.accessory = heavy_weight

        damage = calculate_charge_damage(cavalry_squad, infantry_squad, plain_terrain)
        assert damage == 0.0

    def test_charge_with_zero_unit_count_inflicts_zero_damage(
        self, cavalry_squad, infantry_squad, plain_terrain
    ):
        cavalry_squad.state.unit_count = 0
        damage = calculate_charge_damage(cavalry_squad, infantry_squad, plain_terrain)
        assert damage == 0.0

    def test_charge_against_stationary_target_is_bounded(
        self, cavalry_squad, infantry_squad, plain_terrain
    ):
        # Защитник имеет скорость 0.0. Расчет не должен улетать в бесконечность
        heavy_weight = Equipment(
            id="acc_stone2",
            name="Груз",
            lore="...",
            slot=EquipmentSlot.ACCESSORY,
            category=AccessoryCategory.MISC,
            tier=1,
            stats=EquipmentStats(speed_modifier=-1.0),
        )
        infantry_squad.accessory = heavy_weight
        assert infantry_squad.total_effective_speed == 0.0

        damage = calculate_charge_damage(cavalry_squad, infantry_squad, plain_terrain)
        assert damage > 0.0
        # Ограничено множителем MAX_CHARGE_SPEED_RATIO (3.0): 20 * 30 * 1.5 * 3.0 = 2700.0
        assert damage == pytest.approx(2700.0)

    def test_terrain_charge_penalty_full_absorption(
        self, cavalry_squad, infantry_squad, swamp_terrain
    ):
        damage = calculate_charge_damage(cavalry_squad, infantry_squad, swamp_terrain)
        assert damage == 0.0

    def test_elevation_incline_multipliers(self, cavalry_squad, infantry_squad, plain_terrain):
        flat_damage = calculate_charge_damage(
            cavalry_squad, infantry_squad, plain_terrain, SurfaceIncline.FLAT
        )
        descent_damage = calculate_charge_damage(
            cavalry_squad, infantry_squad, plain_terrain, SurfaceIncline.DESCENT
        )
        ascent_damage = calculate_charge_damage(
            cavalry_squad, infantry_squad, plain_terrain, SurfaceIncline.ASCENT
        )

        assert descent_damage == pytest.approx(flat_damage * 1.3)
        assert ascent_damage == pytest.approx(flat_damage * 0.7)


class TestChargeReactionsEdgeCases:
    def test_counter_charge_correctly_inverts_elevation_for_defender(
        self, cavalry_squad, infantry_squad, plain_terrain
    ):
        # Атакующий бежит с холма (DESCENT) -> защитник встречает его снизу вверх (ASCENT)
        res = resolve_charge_reaction(
            attacker=cavalry_squad,
            defender=infantry_squad,
            reaction=ReactionType.COUNTER_CHARGE,
            attacker_terrain=plain_terrain,
            defender_terrain=plain_terrain,
            elevation=SurfaceIncline.DESCENT,
        )

        expected_attacker_dmg = calculate_charge_damage(
            infantry_squad, cavalry_squad, plain_terrain, SurfaceIncline.ASCENT
        )
        expected_defender_dmg = calculate_charge_damage(
            cavalry_squad, infantry_squad, plain_terrain, SurfaceIncline.DESCENT
        )

        assert res.damage_to_attacker == pytest.approx(expected_attacker_dmg)
        assert res.damage_to_defender == pytest.approx(expected_defender_dmg)

    def test_accept_charge_exact_morale_boundary(
        self, cavalry_squad, infantry_squad, plain_terrain
    ):
        # Порог ровно 35.0
        infantry_squad.state.morale = MORALE_THRESHOLD_ACCEPT_CHARGE
        res_pass = resolve_charge_reaction(
            cavalry_squad,
            infantry_squad,
            ReactionType.ACCEPT_CHARGE,
            plain_terrain,
            plain_terrain,
        )

        assert res_pass.damage_to_attacker > 0.0
        assert res_pass.defender_morale_shock == 0.0

        # Мораль 34.9 -> провал удержания строя
        infantry_squad.state.morale = 34.9
        res_fail = resolve_charge_reaction(
            cavalry_squad,
            infantry_squad,
            ReactionType.ACCEPT_CHARGE,
            plain_terrain,
            plain_terrain,
        )

        assert res_fail.damage_to_attacker == 0.0
        assert res_fail.damage_to_defender > 0.0
        assert res_fail.defender_morale_shock == 10.0

    def test_flee_reaction_inflicts_heavy_casualties_without_retaliation(
        self, cavalry_squad, infantry_squad, plain_terrain
    ):
        res = resolve_charge_reaction(
            cavalry_squad, infantry_squad, ReactionType.FLEE, plain_terrain, plain_terrain
        )

        base_charge = calculate_charge_damage(cavalry_squad, infantry_squad, plain_terrain)
        assert res.damage_to_attacker == 0.0
        assert res.damage_to_defender == pytest.approx(
            base_charge * FLEE_CATCH_DAMAGE_MULTIPLIER
        )
