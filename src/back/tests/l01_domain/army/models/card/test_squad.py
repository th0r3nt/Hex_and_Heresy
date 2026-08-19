"""
Тесты для src/back/l01_domain/army/models/card/squad.py

Фикстуры unit_archetype / weapon / armor / accessory - из
tests/l01_domain/army/conftest.py.
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.army.constants import (
    MAX_MORALE,
    MAX_STAMINA,
    PANIC_THRESHOLD_MORALE,
)
from src.back.l01_domain.army.models.card.squad import Squad, SquadState


class TestSquadState:
    def test_requires_non_negative_unit_count_and_hp(self):
        with pytest.raises(ValidationError):
            SquadState(unit_count=-1, hp_first_unit=10.0)

        with pytest.raises(ValidationError):
            SquadState(unit_count=5, hp_first_unit=-1.0)

    def test_morale_and_stamina_default_to_max(self):
        state = SquadState(unit_count=5, hp_first_unit=10.0)

        assert state.morale == MAX_MORALE
        assert state.stamina == MAX_STAMINA


class TestCreateNew:
    def test_uses_default_unit_count_from_archetype(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype)

        assert squad.state.unit_count == unit_archetype.default_unit_count

    def test_custom_unit_count_overrides_default(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype, custom_unit_count=40)

        assert squad.state.unit_count == 40

    def test_custom_unit_count_zero_falls_back_to_default(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype, custom_unit_count=0)

        assert squad.state.unit_count == unit_archetype.default_unit_count

    def test_morale_and_stamina_start_at_archetype_base(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype)

        assert squad.state.morale == unit_archetype.base_stats.base_morale
        assert squad.state.stamina == unit_archetype.base_stats.base_stamina

    def test_hp_first_unit_starts_at_full_health(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype)

        assert squad.state.hp_first_unit == unit_archetype.base_stats.max_hp


class TestDisplayName:
    def test_unnamed_squad_shows_archetype_name(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype)

        assert squad.display_name == unit_archetype.name

    def test_named_veteran_shows_nickname(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype)
        squad.veterancy.promote(
            commander_name="Маркус",
            squad_nickname="Грязные стрелки Маркуса",
            trait_name="Высокомерные",
            lore="...",
        )

        assert squad.display_name == "Грязные стрелки Маркуса"


class TestEquipmentAggregation:
    def test_bare_squad_uses_only_archetype_armor(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype)

        assert squad.total_effective_armor == unit_archetype.base_stats.base_armor
        assert squad.total_attack_damage == 0.0

    def test_armor_and_accessory_stack_on_top_of_base(self, unit_archetype, armor, accessory):
        squad = Squad.create_new(archetype=unit_archetype, armor=armor, accessory=accessory)

        expected = (
            unit_archetype.base_stats.base_armor
            + armor.stats.armor_bonus
            + accessory.stats.armor_bonus
        )
        assert squad.total_effective_armor == expected

    def test_weapon_and_accessory_damage_stack(self, unit_archetype, weapon, accessory):
        squad = Squad.create_new(archetype=unit_archetype, weapon=weapon, accessory=accessory)

        assert squad.total_attack_damage == weapon.stats.damage + accessory.stats.damage

    def test_accessory_alone_can_deal_damage(self, unit_archetype, accessory):
        # Аксессуар-щит с шипами наносит урон и без основного оружия.
        squad = Squad.create_new(archetype=unit_archetype, accessory=accessory)

        assert squad.total_attack_damage == accessory.stats.damage


class TestUpkeep:
    def test_gold_and_food_scale_with_unit_count(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype, custom_unit_count=50)

        assert squad.upkeep_gold == unit_archetype.base_upkeep_gold * 50
        assert squad.upkeep_food == unit_archetype.base_upkeep_food * 50

    def test_veteran_multiplier_raises_gold_upkeep_only(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype, custom_unit_count=50)
        squad.veterancy.upkeep_gold_multiplier = 1.2

        expected_gold = unit_archetype.base_upkeep_gold * 50 * 1.2
        assert squad.upkeep_gold == pytest.approx(expected_gold)
        # Ветеранская наценка не должна затрагивать провизию.
        assert squad.upkeep_food == unit_archetype.base_upkeep_food * 50


class TestTakeDamage:
    def _fresh_squad(self, unit_archetype, unit_count=5):
        return Squad.create_new(archetype=unit_archetype, custom_unit_count=unit_count)

    def test_zero_or_negative_damage_is_ignored(self, unit_archetype):
        squad = self._fresh_squad(unit_archetype)

        assert squad.take_damage(0.0) == 0
        assert squad.take_damage(-5.0) == 0
        assert squad.state.unit_count == 5

    def test_already_wiped_squad_returns_zero_deaths(self, unit_archetype):
        squad = self._fresh_squad(unit_archetype, unit_count=1)
        squad.state.unit_count = 0

        assert squad.take_damage(100.0) == 0

    def test_minimum_one_damage_gets_through_heavy_armor(self, unit_archetype, armor):
        # Урон меньше брони не должен превращаться в 0 - иначе отряд
        # становится абсолютно неубиваемым.
        squad = Squad.create_new(archetype=unit_archetype, armor=armor, custom_unit_count=1)
        squad.state.hp_first_unit = 1.0

        deaths = squad.take_damage(raw_damage=1.0)  # armor_bonus == 5.0

        assert deaths == 1
        assert squad.state.unit_count == 0

    def test_damage_kills_exact_number_of_units(self, unit_archetype):
        squad = self._fresh_squad(unit_archetype, unit_count=5)  # hp_first_unit == 20.0

        deaths = squad.take_damage(raw_damage=45.0)

        assert deaths == 2
        assert squad.state.unit_count == 3
        assert squad.state.hp_first_unit == 15.0

    def test_armor_piercing_reduces_effective_armor(self, unit_archetype, armor):
        squad = Squad.create_new(archetype=unit_archetype, armor=armor, custom_unit_count=1)
        squad.state.hp_first_unit = 10.0

        # armor_bonus == 5.0, armor_piercing полностью его нейтрализует.
        deaths = squad.take_damage(raw_damage=8.0, armor_piercing=5.0)

        assert deaths == 0
        assert squad.state.hp_first_unit == 2.0

    def test_overkill_wipes_out_squad_cleanly(self, unit_archetype):
        squad = self._fresh_squad(unit_archetype, unit_count=2)

        deaths = squad.take_damage(raw_damage=1000.0)

        assert deaths == 2
        assert squad.state.unit_count == 0
        assert squad.state.hp_first_unit == 0.0


class TestMorale:
    def test_shock_below_threshold_triggers_panic(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype)
        squad.state.morale = 30.0

        squad.apply_morale_shock(15.0)

        assert squad.state.morale == 15.0
        assert squad.state.is_in_panic is True

    def test_morale_cannot_drop_below_zero(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype)
        squad.state.morale = 5.0

        squad.apply_morale_shock(100.0)

        assert squad.state.morale == 0.0

    def test_recover_above_threshold_clears_panic(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype)
        squad.state.morale = 10.0
        squad.state.is_in_panic = True

        squad.recover_morale(50.0)

        assert squad.state.morale == 60.0
        assert squad.state.is_in_panic is False

    def test_recovering_to_exact_threshold_does_not_clear_panic(self, unit_archetype):
        # Пограничный случай: apply_morale_shock ставит панику при morale <= 20,
        # а recover_morale снимает её только при morale > 20 (строгое неравенство).
        # Восстановление ровно до 20 панику НЕ снимет - это асимметрично,
        # но так написан код, и тест это фиксирует явно.
        squad = Squad.create_new(archetype=unit_archetype)
        squad.state.morale = 0.0
        squad.state.is_in_panic = True

        squad.recover_morale(PANIC_THRESHOLD_MORALE)

        assert squad.state.morale == PANIC_THRESHOLD_MORALE
        assert squad.state.is_in_panic is True

    def test_morale_cannot_exceed_max(self, unit_archetype):
        squad = Squad.create_new(archetype=unit_archetype)
        squad.state.morale = MAX_MORALE - 5

        squad.recover_morale(50.0)

        assert squad.state.morale == MAX_MORALE
