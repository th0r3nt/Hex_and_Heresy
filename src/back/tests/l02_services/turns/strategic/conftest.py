"""
Общие фикстуры для тестов стратегического хода.
"""

import pytest

from src.back.l01_domain.army.constants import EquipmentSlot, StrategicMovementPace
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord, LordArchetype, LordTrait
from src.back.l01_domain.maps.models.strategic import HexCoordinates


class FakeEventBus:
    """Фейковая шина событий для фиксации опубликованных сообщений в тестах."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args, **kwargs) -> None:
        self.events.append((event_name, kwargs))


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def human_faction() -> Faction:
    lord = Lord(
        faction_id="humans",
        name="Валленштейн",
        title="Лорд-командующий",
        archetype=LordArchetype(id="arch_lord", name="Бюрократ", description="..."),
        trait=LordTrait(id="trait_lord", name="Расчетливый", text_fragment="..."),
    )
    hq = Headquarters(faction_id="humans", name="Цитадель")
    faction = Faction(
        id="humans",
        race_id="humans",
        name="Священная Империя",
        is_player_controlled=True,
        lord=lord,
        headquarters=hq,
    )
    faction.resources[ResourceType.GOLD] = 500.0
    faction.resources[ResourceType.MATERIAL] = 200.0
    faction.resources[ResourceType.FOOD] = 300.0
    return faction


@pytest.fixture
def orc_faction() -> Faction:
    lord = Lord(
        faction_id="greenskins",
        name="Гром",
        title="Вождь",
        archetype=LordArchetype(id="arch_orc", name="Тиран", description="..."),
        trait=LordTrait(id="trait_orc", name="Жестокий", text_fragment="..."),
    )
    hq = Headquarters(faction_id="greenskins", name="Шатер Вождя")
    faction = Faction(
        id="greenskins",
        race_id="greenskins",
        name="Орда Ржавых Клыков",
        is_player_controlled=False,
        lord=lord,
        headquarters=hq,
    )
    faction.resources[ResourceType.GOLD] = 100.0
    faction.resources[ResourceType.FOOD] = 100.0
    return faction


@pytest.fixture
def basic_squad() -> Squad:
    archetype = UnitArchetype(
        id="unit_human_guard",
        faction_id="humans",
        name="Городская стража",
        tier=1,
        default_unit_count=100,
        base_stats=BaseUnitStats(max_hp=20.0),
        base_upkeep_food=1.0,
        base_upkeep_gold=0.5,
    )
    weapon = Equipment(
        id="wpn_sword",
        name="Меч",
        lore="...",
        slot=EquipmentSlot.WEAPON,
        tier=1,
        stats=EquipmentStats(damage=5.0),
    )
    return Squad.create_new(archetype=archetype, weapon=weapon)


@pytest.fixture
def sample_army(human_faction, basic_squad) -> StrategicArmy:
    army = StrategicArmy(
        faction_id=human_faction.id,
        name="1-й Легион",
        current_hex=HexCoordinates.from_axial(0, 0),
        pace=StrategicMovementPace.MARCH,
    )
    army.add_squad(basic_squad)
    return army
