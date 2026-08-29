"""
Маска тумана войны одной фракции на глобальной карте.

Фракция знает о карте ровно две вещи: что она видит прямо сейчас и что
когда-либо видела. Из этой пары и выводится состояние каждого гекса
(HexVisibilityState) - от черного тумана до полного обзора.

Модель хранит только знание. Кто именно дает обзор (цитадель, вышка,
марширующая колонна) и как далеко он бьет - забота сервиса расчета
видимости в l02_services/mechanics/vision.
"""

from typing import Iterable

from pydantic import BaseModel, Field

from src.back.l01_domain.maps.constants import HexVisibilityState
from src.back.l01_domain.maps.models.strategic import HexCoordinates


class FactionVisionMap(BaseModel):
    """
    Что фракция видит на карте сейчас и что успела открыть за партию.

    Прямой обзор пересчитывается каждый такт с нуля: армия ушла - гекс
    снова затягивает туманом. История открытых гексов, наоборот, только
    растет: увиденное однажды не забывается.
    """

    faction_id: str = Field(..., min_length=1)

    visible_hexes: set[HexCoordinates] = Field(
        default_factory=set,
        description="Гексы под прямым обзором на текущий такт: видно все, включая чужие армии",
    )
    explored_hexes: set[HexCoordinates] = Field(
        default_factory=set,
        description=(
            "Гексы, которые фракция когда-либо видела: ландшафт и застройка "
            "остаются известными и после того, как разведка ушла"
        ),
    )

    spotted_army_ids: set[str] = Field(
        default_factory=set,
        description=(
            "Чужие армии, которые фракция видела на прошлом такте. Нужны, "
            "чтобы отличить только что вскрытого врага от того, что и так "
            "стоит под стенами вторую неделю"
        ),
    )

    # ==================================================================
    # ЧТЕНИЕ СОСТОЯНИЯ
    # ==================================================================

    def get_hex_status(self, coord: HexCoordinates) -> HexVisibilityState:
        """
        Состояние конкретного гекса для этой фракции.

        Прямой обзор старше памяти: гекс под наблюдением всегда VISIBLE,
        даже если он же лежит и в истории открытых.
        """
        if coord in self.visible_hexes:
            return HexVisibilityState.VISIBLE
        if coord in self.explored_hexes:
            return HexVisibilityState.FOG_OF_WAR
        return HexVisibilityState.UNEXPLORED

    def is_visible(self, coord: HexCoordinates) -> bool:
        """Просматривается ли гекс прямо сейчас."""
        return coord in self.visible_hexes

    def is_explored(self, coord: HexCoordinates) -> bool:
        """Открывала ли фракция этот гекс хоть раз за партию."""
        return coord in self.explored_hexes or coord in self.visible_hexes

    # ==================================================================
    # ОБНОВЛЕНИЕ ЗНАНИЯ
    # ==================================================================

    def reveal(self, coords: Iterable[HexCoordinates]) -> set[HexCoordinates]:
        """
        Берет гексы под прямой обзор и заносит их в историю открытых.

        Возвращает те из них, которые фракция увидела впервые: именно о них
        стоит рассказать игроку, а не обо всем поле зрения целиком.
        """
        newly_explored: set[HexCoordinates] = set()

        for coord in coords:
            self.visible_hexes.add(coord)
            if coord not in self.explored_hexes:
                self.explored_hexes.add(coord)
                newly_explored.add(coord)

        return newly_explored

    def track_spotted_armies(self, army_ids: set[str]) -> set[str]:
        """
        Обновляет список чужих армий в поле зрения и возвращает те из них,
        что вскрыты именно сейчас.

        Сравнение идет по самим армиям, а не по гексам: враг может войти в
        давно просматриваемый сектор, и это все равно новость. Ушедшая из
        обзора армия из списка вычеркивается, поэтому ее возвращение снова
        поднимет тревогу.
        """
        newly_spotted = army_ids - self.spotted_army_ids
        self.spotted_army_ids = set(army_ids)
        return newly_spotted

    def clear_direct_vision(self) -> None:
        """
        Гасит прямой обзор перед пересчетом такта.

        История открытых гексов при этом не трогается: фракция забывает,
        где стоит враг, но не то, как выглядит местность.
        """
        self.visible_hexes.clear()
