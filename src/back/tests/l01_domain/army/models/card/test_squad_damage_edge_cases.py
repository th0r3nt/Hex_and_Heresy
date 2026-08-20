"""
Тесты краевых случаев математики урона, бронепробития, скорости и морали отряда.
"""

import pytest

from src.back.l01_domain.army.constants import (
    AccessoryCategory,
    ArmorCategory,
    EquipmentSlot,
    MAX_MORALE,
    MIN_MORALE,
    PANIC_THRESHOLD_MORALE,
    UnitSizeCategory,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.common import FactionRace


@pytest.fixture
def standard_archetype() -> UnitArchetype:
    return UnitArchetype(
        id="unit_heavy_infantry",
        race=FactionRace.HUMANS,
        name="Тяжелая пехота",
        tier=2,
        default_unit_count=100,
        base_stats=BaseUnitStats(
            max_hp=20.0,
            base_armor=2.0,
            base_speed=2.0,
            base_morale=50.0,
            base_stamina=100.0,
            size_category=UnitSizeCategory.MEDIUM,
        ),
    )


class TestSquadTakeDamageEdgeCases:
    def test_damage_exactly_equals_first_unit_hp(self, standard_archetype):
        squad = Squad.create_new(archetype=standard_archetype, custom_unit_count=10)
        # Броня базы = 2.0. При raw_damage = 22.0 net_damage = 20.0 == hp_first_unit
        deaths = squad.take_damage(raw_damage=22.0)

        assert deaths == 1
        assert squad.state.unit_count == 9
        assert squad.state.hp_first_unit == 20.0

    def test_massive_overkill_cleanly_zeros_state(self, standard_archetype):
        squad = Squad.create_new(archetype=standard_archetype, custom_unit_count=10)
        # Суммарное ХП отряда = 200. Наносим 50 000 урона
        deaths = squad.take_damage(raw_damage=50000.0)

        assert deaths == 10
        assert squad.state.unit_count == 0
        assert squad.state.hp_first_unit == 0.0

    def test_damage_to_already_dead_squad_returns_zero(self, standard_archetype):
        squad = Squad.create_new(archetype=standard_archetype, custom_unit_count=0)
        squad.state.unit_count = 0
        squad.state.hp_first_unit = 0.0

        deaths = squad.take_damage(raw_damage=100.0)
        assert deaths == 0
        assert squad.state.unit_count == 0

    def test_extreme_armor_piercing_exceeding_total_armor(self, standard_archetype):
        plate_armor = Equipment(
            id="armor_plate_01",
            name="Латы",
            lore="...",
            slot=EquipmentSlot.ARMOR,
            category=ArmorCategory.PLATE,
            tier=3,
            stats=EquipmentStats(armor_bonus=10.0),
        )
        squad = Squad.create_new(
            archetype=standard_archetype, armor=plate_armor, custom_unit_count=5
        )
        # Общая броня: 2.0 (база) + 10.0 (латы) = 12.0. AP = 100.0
        # Эффективная броня должна быть 0.0, net_damage = 20.0
        deaths = squad.take_damage(raw_damage=20.0, armor_piercing=100.0)

        assert deaths == 1
        assert squad.state.unit_count == 4
        assert squad.state.hp_first_unit == 20.0

    def test_sub_threshold_damage_respects_minimum_one_damage_rule(self, standard_archetype):
        plate_armor = Equipment(
            id="armor_heavy_plate",
            name="Суперлаты",
            lore="...",
            slot=EquipmentSlot.ARMOR,
            category=ArmorCategory.PLATE,
            tier=4,
            stats=EquipmentStats(armor_bonus=50.0),
        )
        squad = Squad.create_new(
            archetype=standard_archetype, armor=plate_armor, custom_unit_count=1
        )
        # Урон меньше брони наносит минимум 1 ед. урона
        deaths = squad.take_damage(raw_damage=5.0)

        assert deaths == 0
        assert squad.state.unit_count == 1
        assert squad.state.hp_first_unit == 19.0

    def test_zero_and_negative_raw_damage_causes_no_effect(self, standard_archetype):
        squad = Squad.create_new(archetype=standard_archetype, custom_unit_count=5)

        assert squad.take_damage(0.0) == 0
        assert squad.take_damage(-50.0) == 0
        assert squad.state.unit_count == 5
        assert squad.state.hp_first_unit == 20.0

    def test_fractional_damage_accumulation(self, standard_archetype):
        squad = Squad.create_new(archetype=standard_archetype, custom_unit_count=2)
        # Броня базы 2.0. Наносим серию скользящих ударов: net_damage = 5.5
        squad.take_damage(raw_damage=7.5)  # hp_first: 20 - 5.5 = 14.5
        assert squad.state.hp_first_unit == pytest.approx(14.5)
        assert squad.state.unit_count == 2

        squad.take_damage(raw_damage=7.5)  # hp_first: 14.5 - 5.5 = 9.0
        assert squad.state.hp_first_unit == pytest.approx(9.0)

        squad.take_damage(raw_damage=12.0)  # net: 10.0 -> 9.0 < 10.0 -> смерть 1 бойца, остаток 1.0 в след.
        assert squad.state.unit_count == 1
        assert squad.state.hp_first_unit == pytest.approx(19.0)


class TestSquadEquipmentAndStatCalculations:
    def test_total_effective_speed_clamped_at_zero(self, standard_archetype):
        heavy_armor = Equipment(
            id="armor_ultra_heavy",
            name="Каменная броня",
            lore="...",
            slot=EquipmentSlot.ARMOR,
            category=ArmorCategory.CARAPACE,
            tier=3,
            stats=EquipmentStats(speed_modifier=-0.8),
        )
        heavy_shield = Equipment(
            id="acc_tower_shield",
            name="Башенный щит",
            lore="...",
            slot=EquipmentSlot.ACCESSORY,
            category=AccessoryCategory.SHIELD,
            tier=2,
            stats=EquipmentStats(speed_modifier=-0.5),
        )
        # Сумма штрафов: -0.8 + -0.5 = -1.3 (-130%)
        squad = Squad.create_new(
            archetype=standard_archetype, armor=heavy_armor, accessory=heavy_shield
        )

        assert squad.total_effective_speed == 0.0

    def test_size_damage_bonus_stacking(self, standard_archetype):
        halberd = Equipment(
            id="wpn_halberd",
            name="Алебарда",
            lore="...",
            slot=EquipmentSlot.WEAPON,
            category=WeaponCategory.POLEARM,
            tier=2,
            stats=EquipmentStats(
                damage=10.0,
                damage_bonus_vs_size={
                    UnitSizeCategory.LARGE: 0.3,
                    UnitSizeCategory.HUGE: 0.5,
                },
            ),
        )
        banner = Equipment(
            id="acc_slayer_banner",
            name="Знамя истребителя гигантов",
            lore="...",
            slot=EquipmentSlot.ACCESSORY,
            category=AccessoryCategory.BANNER,
            tier=3,
            stats=EquipmentStats(
                damage=2.0,
                damage_bonus_vs_size={
                    UnitSizeCategory.HUGE: 0.2,
                },
            ),
        )
        squad = Squad.create_new(
            archetype=standard_archetype, weapon=halberd, accessory=banner
        )

        # Базовый урон = 10 + 2 = 12.0
        assert squad.total_attack_damage == 12.0

        # По средней цели (бонуса нет): 12.0 * 1.0 = 12.0
        assert squad.total_attack_damage_vs(UnitSizeCategory.MEDIUM) == pytest.approx(12.0)

        # По крупной цели (LARGE): бонус 0.3 -> 12.0 * 1.3 = 15.6
        assert squad.total_attack_damage_vs(UnitSizeCategory.LARGE) == pytest.approx(15.6)

        # По гигантской цели (HUGE): бонус 0.5 + 0.2 = 0.7 -> 12.0 * 1.7 = 20.4
        assert squad.total_attack_damage_vs(UnitSizeCategory.HUGE) == pytest.approx(20.4)


class TestSquadMoraleBoundaries:
    def test_morale_panic_boundary_thresholds(self, standard_archetype):
        squad = Squad.create_new(archetype=standard_archetype)
        squad.state.morale = 21.0
        squad.state.is_in_panic = False

        # Удар на 1.0 переводит мораль ровно в 20.0 -> триггер паники
        squad.apply_morale_shock(1.0)
        assert squad.state.morale == PANIC_THRESHOLD_MORALE
        assert squad.state.is_in_panic is True

        # Восстановление ровно до 20.0 не снимает панику (строгое неравенство > 20)
        squad.state.morale = 10.0
        squad.recover_morale(10.0)
        assert squad.state.morale == PANIC_THRESHOLD_MORALE
        assert squad.state.is_in_panic is True

        # Восстановление выше 20.0 снимает панику
        squad.recover_morale(0.1)
        assert squad.state.morale == pytest.approx(20.1)
        assert squad.state.is_in_panic is False

    def test_morale_cannot_exceed_limits(self, standard_archetype):
        squad = Squad.create_new(archetype=standard_archetype)

        squad.apply_morale_shock(999.0)
        assert squad.state.morale == MIN_MORALE

        squad.recover_morale(999.0)
        assert squad.state.morale == MAX_MORALE