"""
Тесты для src/back/l01_domain/army/models/card/equipment.py
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.army.constants import (
    AccessoryCategory,
    ArmorCategory,
    EquipmentSlot,
    EquipmentTag,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
from src.back.l01_domain.exceptions.army import InvalidEquipmentSlotError


class TestEquipmentStats:
    def test_defaults_are_zero_or_neutral(self):
        stats = EquipmentStats()

        assert stats.damage == 0.0
        assert stats.armor_piercing == 0.0
        assert stats.armor_bonus == 0.0
        assert stats.range_hexes == 1
        assert stats.speed_modifier == 0.0
        assert stats.initiative_modifier == 0
        assert stats.stamina_drain_per_turn == 0.0

    @pytest.mark.parametrize(
        "field_name",
        ["damage", "armor_piercing", "armor_bonus", "stamina_drain_per_turn"],
    )
    def test_negative_values_are_rejected(self, field_name):
        with pytest.raises(ValidationError):
            EquipmentStats(**{field_name: -1.0})

    def test_range_hexes_must_be_at_least_one(self):
        with pytest.raises(ValidationError):
            EquipmentStats(range_hexes=0)

    def test_speed_and_initiative_modifiers_can_be_negative(self):
        stats = EquipmentStats(speed_modifier=-0.2, initiative_modifier=-1)

        assert stats.speed_modifier == -0.2
        assert stats.initiative_modifier == -1

    def test_is_frozen(self):
        stats = EquipmentStats(damage=5.0)

        with pytest.raises(ValidationError):
            stats.damage = 10.0


class TestEquipment:
    def _make(self, **overrides) -> Equipment:
        payload = dict(
            id="weapon_test_halberd",
            name="Тестовая алебарда",
            lore="Простое оружие для проверки модели.",
            slot=EquipmentSlot.WEAPON,
            category=WeaponCategory.POLEARM,
            tags={EquipmentTag.TWO_HANDED, EquipmentTag.BRACEABLE},
            tier=2,
        )
        payload.update(overrides)
        return Equipment(**payload)

    def test_minimal_construction_uses_default_stats(self):
        item = self._make()

        assert item.stats == EquipmentStats()
        assert item.cost_gold == 0.0
        assert item.cost_material == 0.0
        assert item.is_custom is False
        assert item.special_rules is None
        assert item.has_tag(EquipmentTag.BRACEABLE) is True
        assert item.is_braceable is True
        assert item.is_two_handed is True
        assert item.is_firearm is False

    def test_firearm_tags_and_properties(self):
        arquebus = self._make(
            id="weapon_human_arquebus",
            category=WeaponCategory.FIREARM,
            tags={EquipmentTag.BLACKPOWDER, EquipmentTag.TWO_HANDED},
        )
        assert arquebus.is_firearm is True
        assert arquebus.has_tag(EquipmentTag.BLACKPOWDER) is True

    def test_slot_category_mismatch_raises_domain_error(self):
        # Попытка надеть латы в слот оружия
        with pytest.raises(InvalidEquipmentSlotError):
            self._make(
                slot=EquipmentSlot.WEAPON,
                category=ArmorCategory.PLATE,
            )

        # Попытка надеть щит в слот брони
        with pytest.raises(InvalidEquipmentSlotError):
            self._make(
                slot=EquipmentSlot.ARMOR,
                category=AccessoryCategory.SHIELD,
            )

    @pytest.mark.parametrize("field_name", ["id", "name", "lore"])
    def test_empty_strings_are_rejected(self, field_name):
        with pytest.raises(ValidationError):
            self._make(**{field_name: ""})

    @pytest.mark.parametrize("tier", [-1, 7])
    def test_tier_out_of_bounds_is_rejected(self, tier):
        with pytest.raises(ValidationError):
            self._make(tier=tier)

    @pytest.mark.parametrize("tier", [0, 6])
    def test_tier_boundaries_are_accepted(self, tier):
        item = self._make(tier=tier)
        assert item.tier == tier

    def test_custom_equipment_carries_special_rules(self):
        item = self._make(
            is_custom=True,
            special_rules="Развертывание: наносит 50 ед. урона первому вошедшему отряду.",
        )

        assert item.is_custom is True
        assert "50 ед." in item.special_rules

    def test_is_frozen(self):
        item = self._make()

        with pytest.raises(ValidationError):
            item.cost_gold = 999.0
