"""
Тесты доменных инвариантов фракционной казны, списания ресурсов,
лимитов уровней Цитадели и Ратуш.
"""

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions.factions import (
    BuildingMaxLevelReachedError,
    InsufficientResourcesError,
    NegativeResourceAmountError,
)
from src.back.l01_domain.factions.constants import ResourceType, TOWNHALL_MAX_BUILDING_SLOTS
from src.back.l01_domain.factions.models.buildings import (
    Headquarters,
    RegionalHall,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord


@pytest.fixture
def faction() -> Faction:
    lord = Lord(
        faction_id="test_fac",
        name="Лорд",
        title="Барон",
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


class TestAtomicPurchase:
    """
    Покупка неделима: предмет стоит и золота, и материалов, и заплатить
    половину цены нельзя.
    """

    def test_affordable_purchase_debits_everything(self, faction):
        faction.spend_all({ResourceType.GOLD: 60.0, ResourceType.FOOD: 20.0})

        assert faction.resources[ResourceType.GOLD] == 40.0
        assert faction.resources[ResourceType.FOOD] == 30.0

    def test_shortage_leaves_the_treasury_untouched(self, faction):
        """Золота хватает, провизии нет - не списывается ничего."""
        with pytest.raises(InsufficientResourcesError) as exc_info:
            faction.spend_all({ResourceType.GOLD: 60.0, ResourceType.FOOD: 500.0})

        assert exc_info.value.resource == "food"
        assert faction.resources[ResourceType.GOLD] == 100.0
        assert faction.resources[ResourceType.FOOD] == 50.0

    def test_shortage_on_the_first_resource_also_changes_nothing(self, faction):
        with pytest.raises(InsufficientResourcesError) as exc_info:
            faction.spend_all({ResourceType.GOLD: 500.0, ResourceType.FOOD: 20.0})

        assert exc_info.value.resource == "gold"
        assert faction.resources[ResourceType.GOLD] == 100.0
        assert faction.resources[ResourceType.FOOD] == 50.0

    def test_exact_amounts_are_affordable(self, faction):
        """Ровно вся казна - это по карману, а не нехватка."""
        faction.spend_all({ResourceType.GOLD: 100.0, ResourceType.FOOD: 50.0})

        assert faction.resources[ResourceType.GOLD] == 0.0
        assert faction.resources[ResourceType.FOOD] == 0.0

    def test_empty_purchase_changes_nothing(self, faction):
        faction.spend_all({})

        assert faction.resources[ResourceType.GOLD] == 100.0


class TestBuildingLevelAndSlotsInvariants:
    def test_headquarters_slots_and_max_level_six(self):
        hq = Headquarters(faction_id="f1", name="Цитадель", level=1)
        assert hq.building_slots == 4

        for _ in range(5):
            hq.upgrade()

        assert hq.level == 6
        assert hq.building_slots == 9

        with pytest.raises(BuildingMaxLevelReachedError) as exc_info:
            hq.upgrade()

        assert exc_info.value.building_name == "Цитадель"
        assert exc_info.value.max_level == 6

    def test_regional_hall_slots_and_max_level_three(self):
        hall = RegionalHall(faction_id="f1", zone_id="zone_01", name="Ратуша", level=1)
        assert hall.building_slots == 1

        hall.upgrade()
        assert hall.level == 2
        assert hall.building_slots == 2

        hall.upgrade()
        assert hall.level == 3
        assert hall.building_slots == 3
        assert hall.building_slots == TOWNHALL_MAX_BUILDING_SLOTS

        with pytest.raises(BuildingMaxLevelReachedError) as exc_info:
            hall.upgrade()

        assert exc_info.value.max_level == 3
