"""
Разметка карты: кто из сторон где встанет.

Считается раньше всего остального, потому что от нее зависят и застройка, и
стартовые армии, и то, какие гексы вообще останутся Ничьей землей.

Модульные функции, а не класс: разметке нужны только настройки партии и
жребий - ни каталогов геймдаты, ни шины событий, ни собственного состояния.
"""

from dataclasses import dataclass
from random import Random

from src.back.l01_domain.maps.constants import HexDirection
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    get_standard_base_coordinates,
    hex_neighbor,
)
from src.back.l01_domain.world.constants import (
    BARONY_ALLIED_DIRECTIONS,
    BARONY_CENTER_Q_RANGE,
    BARONY_CENTER_ROW_R,
    NORTH_BASE_ALLIED_DIRECTIONS,
    SOUTH_BASE_ALLIED_DIRECTIONS,
    STARTING_ALLIED_LANDS_COUNT,
)
from src.back.l01_domain.world.models.setup import NewGameConfig


@dataclass(frozen=True)
class FactionPlacement:
    """
    Место одной стороны на карте: гекс ее цитадели и обжитые лепестки.

    Порядок лепестков значим - по нему раскладывается стартовая застройка
    (см. factions.py).
    """

    capital_hex: HexCoordinates
    allied_hexes: tuple[HexCoordinates, ...]


# ==================================================================
# РАЗМЕТКА СТОРОН
# ==================================================================


def plan_placements(config: NewGameConfig, rng: Random) -> list[FactionPlacement]:
    """
    Раскладывает стороны по карте в том же порядке, в каком их перечисляют
    настройки: игрок на Северной цитадели, соперник на Южной, баронства -
    где-то в центре Ничьей земли.
    """
    north_base, south_base = get_standard_base_coordinates()

    placements = [
        place_at(north_base, NORTH_BASE_ALLIED_DIRECTIONS),
        place_at(south_base, SOUTH_BASE_ALLIED_DIRECTIONS),
    ]

    if config.include_baronies:
        placements.append(place_at(pick_barony_hex(rng), BARONY_ALLIED_DIRECTIONS))

    return placements


def place_at(
    capital_hex: HexCoordinates, directions: tuple[HexDirection, ...]
) -> FactionPlacement:
    """
    Достраивает к гексу цитадели ее обжитые лепестки по заданным направлениям.
    """
    allied_hexes = tuple(
        hex_neighbor(capital_hex, direction)
        for direction in directions[:STARTING_ALLIED_LANDS_COUNT]
    )
    return FactionPlacement(capital_hex=capital_hex, allied_hexes=allied_hexes)


def pick_barony_hex(rng: Random) -> HexCoordinates:
    """
    Выбирает гекс под замок барона: экваториальный ряд и небольшой разброс по
    горизонтали, чтобы обеим цитаделям баронства мешали одинаково.
    """
    min_q, max_q = BARONY_CENTER_Q_RANGE
    return HexCoordinates.from_axial(rng.randint(min_q, max_q), BARONY_CENTER_ROW_R)
