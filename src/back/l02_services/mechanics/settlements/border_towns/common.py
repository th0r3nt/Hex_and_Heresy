"""
Общее для всех частей механики пограничных городов: поиск участников
приказа и работа с занятостью гексов карты.

Модульные функции, а не класс: у этих операций нет ни состояния, ни шины
событий - им нужен только мир. Класс здесь был бы пустой оберткой.
"""

from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.exceptions.factions import (
    BorderTownNotFoundError,
    FactionNotFoundError,
    InvalidSettlementPlacementError,
)
from src.back.l01_domain.exceptions.workers import InvalidAssignmentTargetError
from src.back.l01_domain.factions.models.border_town import BorderTown
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.models.strategic import HexCoordinates, hex_zone_id
from src.back.l01_domain.world.models.state import WorldState

# ==================================================================
# ПОИСК УЧАСТНИКОВ ПРИКАЗА
# ==================================================================


def require_faction(world_state: WorldState, faction_id: str) -> Faction:
    """Фракция-заказчик приказа либо доменная ошибка."""
    faction = world_state.get_faction(faction_id)
    if faction is None:
        raise FactionNotFoundError(faction_id)
    return faction


def require_town(faction: Faction, town_id: str) -> BorderTown:
    """Город из владений известной фракции либо доменная ошибка."""
    town = faction.get_border_town(town_id)
    if town is None:
        raise BorderTownNotFoundError(town_id=town_id, faction_id=faction.id)
    return town


def require_town_on_map(
    world_state: WorldState, town_id: str
) -> tuple[Faction, BorderTown]:
    """
    Находит город на карте вместе с его владельцем.

    В отличие от require_town, фракция здесь не задана заранее: судьбу
    города решает чужая армия, которой владелец поселения не известен.
    """
    found = world_state.find_border_town(town_id)
    if found is None:
        raise BorderTownNotFoundError(town_id=town_id)
    return found


def require_army(world_state: WorldState, army_id: str) -> StrategicArmy:
    """Армия-исполнитель приказа либо доменная ошибка."""
    army = world_state.get_army(army_id)
    if army is None:
        raise InvalidAssignmentTargetError(army_id, "армия не найдена")
    return army


# ==================================================================
# ЗАНЯТОСТЬ ГЕКСОВ КАРТЫ
# ==================================================================


def assert_hex_is_free(
    world_state: WorldState, faction_id: str, coord: HexCoordinates
) -> None:
    """
    Убеждается, что гекс действительно ничей.

    Занятым считается все, что уже кому-то принадлежит или на чем стоит
    чужая сила: столица и союзные земли любой фракции (включая свои
    собственные - второй город на той же земле не поставить), ориентир
    Ничьей земли и вражеское войско на самом гексе.
    """
    zone_id = hex_zone_id(coord)

    for faction in world_state.factions.values():
        if faction.capital_hex == coord:
            raise InvalidSettlementPlacementError(
                zone_id, f"здесь стоит цитадель фракции '{faction.id}'"
            )
        if zone_id in faction.controlled_zone_ids:
            raise InvalidSettlementPlacementError(
                zone_id, f"земля уже принадлежит фракции '{faction.id}'"
            )

    if world_state.get_point_of_interest_at(coord) is not None:
        raise InvalidSettlementPlacementError(
            zone_id, "гекс занят ориентиром Ничьей земли"
        )

    foreign_army = next(
        (
            army
            for army in world_state.get_armies_at_hex(coord)
            if army.faction_id != faction_id
        ),
        None,
    )
    if foreign_army is not None:
        raise InvalidSettlementPlacementError(
            zone_id, f"на гексе стоит чужое войско '{foreign_army.name}'"
        )


def occupy_hex(world_state: WorldState, coord: HexCoordinates) -> None:
    """
    Вычеркивает гекс из Ничьей земли: он больше не нейтральный, и
    экспедиции рабочих туда уже не отправить.
    """
    if coord in world_state.neutral_hexes:
        world_state.neutral_hexes.remove(coord)


def release_hex(world_state: WorldState, coord: HexCoordinates) -> None:
    """
    Возвращает гекс в Ничью землю - обратная сторона occupy_hex.

    На пепелище сожженного города снова можно ставить поселение и
    отправлять туда экспедиции: земля стала ничьей.
    """
    if coord not in world_state.neutral_hexes:
        world_state.neutral_hexes.append(coord)
