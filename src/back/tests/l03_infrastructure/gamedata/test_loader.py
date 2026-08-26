"""
Тесты инфраструктурного загрузчика статической геймдаты и сессионного реестра.
"""

import pytest

from src.back.l01_domain.army.constants import EquipmentSlot, WeaponCategory
from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.factions.constants import BuildingCategory
from src.back.l03_infrastructure.gamedata.loader import (
    SessionGameDataRepository,
    build_static_registry,
)


class TestStaticGameDataRegistry:
    def test_build_static_registry_loads_real_data(self):
        registry = build_static_registry()

        peasant_mob = registry.get_unit_archetype("unit_bar_serfs_mob_00")
        assert peasant_mob is not None
        assert peasant_mob.name == "Толпа крепостных"

        halberd = registry.get_equipment("wpn_hum_steel_halberd_02")
        assert halberd is not None
        assert halberd.category == WeaponCategory.POLEARM

        watchtower = registry.get_building("bld_hum_watchtower")
        assert watchtower is not None
        assert watchtower.category == BuildingCategory.DEFENSIVE

        human_units = registry.list_faction_units("humans")
        assert len(human_units) > 0

        baronial_buildings = registry.list_faction_buildings("baronial_troops")
        assert len(baronial_buildings) > 0


class TestSessionGameDataRepository:
    @pytest.fixture
    def static_registry(self):
        return build_static_registry()

    def test_session_repository_merges_static_and_custom_equipment(self, static_registry):
        custom_weapon = Equipment(
            id="wpn_custom_flaming_sword",
            name="Пылающий меч",
            lore="Создано оружейником.",
            slot=EquipmentSlot.WEAPON,
            category=WeaponCategory.SWORD,
            tier=4,
            is_custom=True,
        )

        session_repo = SessionGameDataRepository(
            static_registry=static_registry, custom_equipment=[custom_weapon]
        )

        found_custom = session_repo.get_equipment("wpn_custom_flaming_sword")
        assert found_custom is not None
        assert found_custom.name == "Пылающий меч"

        found_static = session_repo.get_equipment("wpn_hum_steel_halberd_02")
        assert found_static is not None

        human_equipment = session_repo.list_faction_equipment("humans")
        custom_ids = [eq.id for eq in human_equipment if eq.is_custom]
        assert "wpn_custom_flaming_sword" in custom_ids

    def test_session_repository_delegates_units_and_buildings(self, static_registry):
        session_repo = SessionGameDataRepository(
            static_registry=static_registry, custom_equipment=[]
        )

        assert session_repo.get_unit_archetype("unit_bar_serfs_mob_00") is not None
        assert session_repo.get_building("bld_hum_watchtower") is not None
