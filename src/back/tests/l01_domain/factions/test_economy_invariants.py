"""
Тесты доменных инвариантов фракционной казны, списания ресурсов,
лимитов уровней Цитадели и Ратуш.
"""

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions import (
    BuildingMaxLevelReachedError,
    InsufficientResourcesError,
    NegativeResourceAmountError,
)
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.buildings import (
    Headquarters,
    RegionalHall,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord, LordArchetype, LordTrait


@pytest.fixture
def faction() -> Faction:
    lord = Lord(
        faction_id="test_fac",
        name="Лорд",
        title="Барон",
        archetype=LordArchetype(id="arch", name="A", description="D"),
        trait=LordTrait(id="tr", name="T", text_fragment="..."),
    )
    hq = Headquarters(faction_id="test_fac", name="Цитадель", level=1)
    f = Faction(
        id="test_fac",
        race=FactionRace.HUMANS,
        name="Фракция",
        lord=lord,
        headquarters=hq,
    )
    f.resources[ResourceType.GOLD] = 100.0
    f.resources[ResourceType.FOOD] = 50.0
    return f


class TestFactionResourceInvariants:
    def test_spend_exact_amount_zeros_balance(self, faction):
        faction.spend(ResourceType.GOLD, 100.0)
        assert faction.resources[ResourceType.GOLD] == 0.0

    def test_spend_more_than_available_raises_insufficient_resources_error(self, faction):
        with pytest.raises(InsufficientResourcesError) as exc_info:
            faction.spend(ResourceType.GOLD, 100.01)

        assert exc_info.value.resource == "gold"
        assert exc_info.value.required == 100.01
        assert exc_info.value.available == 100.0
        assert exc_info.value.faction_id == "test_fac"

    def test_earn_negative_amount_raises_error(self, faction):
        with pytest.raises(NegativeResourceAmountError):
            faction.earn(ResourceType.FOOD, -20.0)


class TestBuildingLevelAndSlotsInvariants:
    def test_headquarters_slots_and_max_level_six(self):
        hq = Headquarters(faction_id="f1", name="Цитадель", level=1)
        # Уровень 1: 4 слота
        assert hq.building_slots == 4

        # Апгрейд до 6 уровня: 4 + (6 - 1) * 1 = 9 слотов
        for _ in range(5):
            hq.upgrade()

        assert hq.level == 6
        assert hq.building_slots == 9

        # Попытка улучшить выше максимального 6 уровня
        with pytest.raises(BuildingMaxLevelReachedError) as exc_info:
            hq.upgrade()

        assert exc_info.value.building_name == "Цитадель"
        assert exc_info.value.max_level == 6

    def test_regional_hall_slots_and_max_level_two(self):
        hall = RegionalHall(faction_id="f1", zone_id="zone_01", name="Ратуша", level=1)
        # Уровень 1: 1 слот
        assert hall.building_slots == 1

        hall.upgrade()
        # Уровень 2: 2 слота
        assert hall.level == 2
        assert hall.building_slots == 2

        # Попытка улучшить выше максимального 2 уровня
        with pytest.raises(BuildingMaxLevelReachedError):
            hall.upgrade()
