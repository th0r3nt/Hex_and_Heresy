"""
Общие фикстуры для тестирования тактической подсистемы боя.
"""

import pytest

from src.back.l01_domain.army.constants import EquipmentSlot, UnitSizeCategory
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.combat.constants import BattleMapSize
from src.back.l01_domain.combat.models.state import TacticalBattleState, TacticalCellState
from src.back.l01_domain.maps.models.tactical import CellCoordinates


class FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, event_name: str, *args, **kwargs) -> None:
        self.events.append((event_name, kwargs))


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def base_stats_human() -> BaseUnitStats:
    return BaseUnitStats(
        max_hp=20.0,
        base_armor=0.0,
        base_speed=2.0,
        base_morale=50.0,
        base_stamina=100.0,
        base_initiative=10,
        size_category=UnitSizeCategory.MEDIUM,
    )


@pytest.fixture
def archetype_human_sword(base_stats_human) -> UnitArchetype:
    return UnitArchetype(
        id="unit_human_swordsmen", # TODO: типизировать
        faction_id="humans", # TODO: типизировать
        name="Мечники",
        tier=1,
        default_unit_count=100,
        base_stats=base_stats_human,
    )


@pytest.fixture
def weapon_sword() -> Equipment:
    return Equipment(
        id="wpn_sword",
        name="Меч",
        lore="...",
        slot=EquipmentSlot.WEAPON,
        tier=1,
        stats=EquipmentStats(damage=5.0, armor_piercing=1.0, range_hexes=1),
    )


@pytest.fixture
def weapon_bow() -> Equipment:
    return Equipment(
        id="wpn_bow",
        name="Лук",
        lore="...",
        slot=EquipmentSlot.WEAPON,
        tier=1,
        stats=EquipmentStats(damage=4.0, range_hexes=6),
    )


@pytest.fixture
def empty_battle_state() -> TacticalBattleState:
    """Пустое поле 14x14 без отрядов."""
    state = TacticalBattleState(map_size=BattleMapSize.SMALL)
    width, height = 14, 14
    for x in range(width):
        for y in range(height):
            state.cells.append(TacticalCellState(coordinates=CellCoordinates(x=x, y=y)))
    return state


def place_squad_on_grid(
    battle_state: TacticalBattleState, squad_id: str, x: int, y: int
) -> None:
    for cell in battle_state.cells:
        if cell.coordinates.x == x and cell.coordinates.y == y:
            cell.occupant_squad_id = squad_id
            break
