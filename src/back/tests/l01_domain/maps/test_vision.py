"""
Маска тумана войны и геометрия обзора.

Проверяется главное правило подсистемы: гекс проходит путь
UNEXPLORED -> VISIBLE -> FOG_OF_WAR и назад в VISIBLE, но никогда не
возвращается в черный туман - однажды увиденное не забывается.
"""

import pytest

from src.back.l01_domain.maps.constants import (
    HexVisibilityState,
    VISION_RADIUS_ARMY,
    VISION_RADIUS_BASE,
    VISION_RADIUS_REGIONAL_HALL,
    VISION_RADIUS_WATCHTOWER,
)
from src.back.l01_domain.exceptions.maps import InvalidZoneIdError
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    hex_from_zone_id,
    hex_spiral,
    hex_zone_id,
)
from src.back.l01_domain.world.models.visibility import FactionVisionMap


CENTER = HexCoordinates.from_axial(0, 0)


@pytest.fixture
def vision_map() -> FactionVisionMap:
    return FactionVisionMap(faction_id="humans")


# ==================================================================
# ГЕОМЕТРИЯ ЗОН ОБЗОРА
# ==================================================================


class TestVisionGeometry:
    def test_base_covers_nineteen_hexes(self):
        """Цитадель радиусом 2 держит под обзором себя и два кольца вокруг."""
        covered = hex_spiral(CENTER, VISION_RADIUS_BASE)

        assert len(covered) == 19  # 1 + 6 + 12
        assert CENTER in covered

    def test_regional_hall_covers_only_its_ring(self):
        """Ратуша радиусом 1 видит себя и шесть соседей - и ни гексом дальше."""
        covered = hex_spiral(CENTER, VISION_RADIUS_REGIONAL_HALL)

        assert len(covered) == 7
        assert HexCoordinates.from_axial(2, 0) not in covered

    def test_watchtower_reaches_as_far_as_a_citadel(self):
        """Вышка светит на те же два гекса, что и цитадель: она для того и ставится."""
        assert VISION_RADIUS_WATCHTOWER == VISION_RADIUS_BASE

    def test_army_sees_only_its_neighbours(self):
        """Марширующая колонна вскрывает лишь ближний круг."""
        covered = hex_spiral(CENTER, VISION_RADIUS_ARMY)

        assert len(covered) == 7

    def test_overlapping_sources_do_not_double_count(self):
        """
        Два источника рядом дают объединение зон, а не сумму: один и тот же
        гекс нельзя увидеть дважды.
        """
        first = set(hex_spiral(CENTER, 1))
        second = set(hex_spiral(HexCoordinates.from_axial(1, 0), 1))

        assert len(first | second) < len(first) + len(second)


# ==================================================================
# СОСТОЯНИЯ ГЕКСА
# ==================================================================


class TestHexVisibilityStates:
    def test_untouched_hex_is_unexplored(self, vision_map: FactionVisionMap):
        assert vision_map.get_hex_status(CENTER) == HexVisibilityState.UNEXPLORED
        assert not vision_map.is_explored(CENTER)

    def test_revealed_hex_becomes_visible(self, vision_map: FactionVisionMap):
        vision_map.reveal([CENTER])

        assert vision_map.get_hex_status(CENTER) == HexVisibilityState.VISIBLE
        assert vision_map.is_visible(CENTER)
        assert vision_map.is_explored(CENTER)

    def test_lost_direct_vision_leaves_fog_of_war(self, vision_map: FactionVisionMap):
        """Разведка ушла - остается память о местности, а не черный туман."""
        vision_map.reveal([CENTER])
        vision_map.clear_direct_vision()

        assert vision_map.get_hex_status(CENTER) == HexVisibilityState.FOG_OF_WAR
        assert not vision_map.is_visible(CENTER)
        assert vision_map.is_explored(CENTER)

    def test_returning_scouts_restore_direct_vision(self, vision_map: FactionVisionMap):
        vision_map.reveal([CENTER])
        vision_map.clear_direct_vision()
        vision_map.reveal([CENTER])

        assert vision_map.get_hex_status(CENTER) == HexVisibilityState.VISIBLE

    def test_hex_never_returns_to_black_fog(self, vision_map: FactionVisionMap):
        """Открытый однажды гекс не забывается до конца партии."""
        vision_map.reveal([CENTER])

        for _ in range(5):
            vision_map.clear_direct_vision()

        assert vision_map.get_hex_status(CENTER) != HexVisibilityState.UNEXPLORED


# ==================================================================
# ОТКРЫТИЕ НОВЫХ ГЕКСОВ
# ==================================================================


class TestReveal:
    def test_reveal_returns_only_first_time_hexes(self, vision_map: FactionVisionMap):
        """
        Во второй раз тот же гекс новостью не считается: интерфейсу незачем
        перерисовывать давно открытую местность.
        """
        first_wave = vision_map.reveal(hex_spiral(CENTER, 1))
        second_wave = vision_map.reveal(hex_spiral(CENTER, 1))

        assert len(first_wave) == 7
        assert second_wave == set()

    def test_reveal_reports_only_the_new_ring(self, vision_map: FactionVisionMap):
        """Расширение обзора приносит ровно прирост, а не всю зону заново."""
        vision_map.reveal(hex_spiral(CENTER, 1))
        grown = vision_map.reveal(hex_spiral(CENTER, 2))

        assert len(grown) == 12  # второе кольцо
        assert len(vision_map.explored_hexes) == 19

    def test_clearing_vision_keeps_history(self, vision_map: FactionVisionMap):
        vision_map.reveal(hex_spiral(CENTER, 2))
        vision_map.clear_direct_vision()

        assert vision_map.visible_hexes == set()
        assert len(vision_map.explored_hexes) == 19


# ==================================================================
# КЛЮЧ ЗОНЫ И ОБРАТНЫЙ РАЗБОР
# ==================================================================


class TestZoneIdRoundTrip:
    @pytest.mark.parametrize(
        "axial",
        [(0, 0), (4, -8), (-4, 8), (-12, 3), (9, 9)],
    )
    def test_zone_id_survives_round_trip(self, axial: tuple[int, int]):
        """
        Здания хранят гекс строкой, а обзору нужен сам гекс: разбор ключа
        обязан возвращать ровно исходную координату.
        """
        coord = HexCoordinates.from_axial(*axial)

        assert hex_from_zone_id(hex_zone_id(coord)) == coord

    def test_broken_zone_id_is_rejected(self):
        with pytest.raises(InvalidZoneIdError):
            hex_from_zone_id("не координаты")
