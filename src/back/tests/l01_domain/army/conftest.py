"""
Общие фикстуры для тестов src/back/l01_domain/army/.
"""

import pytest

from src.back.l01_domain.army.constants import (
    AccessoryCategory,
    ArmorCategory,
    EquipmentSlot,
    EquipmentTag,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.common import FactionRace


@pytest.fixture
def base_unit_stats() -> BaseUnitStats:
    """20 хп, без врождённой брони, базовая мораль 50."""
    return BaseUnitStats(max_hp=20.0)


@pytest.fixture
def unit_archetype(base_unit_stats: BaseUnitStats) -> UnitArchetype:
    return UnitArchetype(
        id="unit_test_infantry",
        race=FactionRace.HUMANS,
        faction_id="humans",
        name="Тестовая пехота",
        tier=1,
        default_unit_count=100,
        base_stats=base_unit_stats,
        base_upkeep_food=1.0,
        base_upkeep_gold=0.5,
    )


@pytest.fixture
def weapon() -> Equipment:
    return Equipment(
        id="weapon_test_sword",
        name="Тестовый меч",
        lore="Обычный меч для теста.",
        slot=EquipmentSlot.WEAPON,
        category=WeaponCategory.SWORD,
        tags={EquipmentTag.ONE_HANDED},
        tier=1,
        stats=EquipmentStats(damage=10.0),
    )


@pytest.fixture
def armor() -> Equipment:
    return Equipment(
        id="armor_test_cuirass",
        name="Тестовая кираса",
        lore="Обычная кираса для теста.",
        slot=EquipmentSlot.ARMOR,
        category=ArmorCategory.PLATE,
        tags={EquipmentTag.HEAVY},
        tier=1,
        stats=EquipmentStats(armor_bonus=5.0),
    )


@pytest.fixture
def accessory() -> Equipment:
    return Equipment(
        id="accessory_test_shield",
        name="Тестовый щит",
        lore="Обычный щит для теста.",
        slot=EquipmentSlot.ACCESSORY,
        category=AccessoryCategory.SHIELD,
        tags={EquipmentTag.ONE_HANDED},
        tier=1,
        stats=EquipmentStats(damage=2.0, armor_bonus=3.0),
    )
