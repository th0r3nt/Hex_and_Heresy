"""
BorderTown - пограничный город: отдельное поселение, которое фракция
основывает на свободном гексе где угодно на карте.

От столицы город отличается двумя вещами:

* союзные земли ему не даны, а покупаются. Город "заселяет" до
  MAX_BORDER_TOWN_ALLIED_LANDS смежных гексов, и на каждом таком гексе
  встает обычная ратуша (RegionalHall) со своими слотами и налогом;
* потолок роста ниже цитадели - четвертый уровень. Каждый уровень
  открывает внутри самого города еще один строительный слот.

Модель держит только свои инварианты (уровень, смежность и лимит земель).
Вопросы "свободен ли гекс" и "хватит ли казны" решает сервисный слой:
доменная модель карты мира не видит.
"""

from uuid import uuid4

from pydantic import BaseModel, Field

from src.back.l01_domain.exceptions.factions import (
    BorderTownMaxLandsReachedError,
    BorderTownMaxLevelReachedError,
    HexNotAdjacentToTownError,
)
from src.back.l01_domain.factions.constants import (
    BORDER_TOWN_BASE_BUILDING_SLOTS,
    BORDER_TOWN_BUILDING_SLOTS_PER_LEVEL,
    MAX_BORDER_TOWN_ALLIED_LANDS,
    MAX_BORDER_TOWN_LEVEL,
    MIN_BORDER_TOWN_LEVEL,
    ResourceType,
)
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    hex_distance,
    hex_zone_id,
)


class BorderTown(BaseModel):
    """
    Агрегат одного пограничного города фракции.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    faction_id: str = Field(..., min_length=1, description="Кому принадлежит город")
    name: str = Field(..., min_length=1, description="Как город назвал основатель")

    level: int = Field(
        default=MIN_BORDER_TOWN_LEVEL,
        ge=MIN_BORDER_TOWN_LEVEL,
        le=MAX_BORDER_TOWN_LEVEL,
    )

    center_hex: HexCoordinates = Field(..., description="Гекс, на котором стоит город")
    claimed_hexes: list[HexCoordinates] = Field(
        default_factory=list,
        description="Выкупленные смежные гексы - союзные земли этого города",
    )

    invested_resources: dict[ResourceType, float] = Field(
        default_factory=dict,
        description=(
            "Все, что фракция вложила в город: основание, апгрейды и выкуп земель. "
            "От этой суммы отсчитывается добыча захватчика, разорившего город"
        ),
    )

    # ==================================================================
    # РАСЧЕТНЫЕ СВОЙСТВА
    # ==================================================================

    @property
    def zone_id(self) -> str:
        """Ключ земли самого города - той, на которой стоит ратуша поселения."""
        return hex_zone_id(self.center_hex)

    @property
    def claimed_zone_ids(self) -> list[str]:
        """Ключи земель, заселенных городом."""
        return [hex_zone_id(coord) for coord in self.claimed_hexes]

    @property
    def building_slots(self) -> int:
        """
        Сколько построек помещается внутри самого города: 2 на первом
        уровне и по одной за каждый следующий (5 на четвертом).
        """
        return (
            BORDER_TOWN_BASE_BUILDING_SLOTS
            + max(0, self.level - MIN_BORDER_TOWN_LEVEL)
            * BORDER_TOWN_BUILDING_SLOTS_PER_LEVEL
        )

    @property
    def free_land_slots(self) -> int:
        """Сколько смежных гексов город еще может выкупить."""
        return max(0, MAX_BORDER_TOWN_ALLIED_LANDS - len(self.claimed_hexes))

    def owns_hex(self, coord: HexCoordinates) -> bool:
        """Стоит ли город на этом гексе или уже заселил его."""
        return coord == self.center_hex or coord in self.claimed_hexes

    # ==================================================================
    # РОСТ ГОРОДА
    # ==================================================================

    def assert_can_upgrade(self) -> None:
        """
        Проверяет потолок уровня, ничего не меняя.

        Отдельно от самого upgrade(), потому что сервис обязан убедиться в
        допустимости приказа до того, как спишет казну: иначе фракция
        заплатила бы за апгрейд, который все равно не состоится.
        """
        if self.level >= MAX_BORDER_TOWN_LEVEL:
            raise BorderTownMaxLevelReachedError(self.name, MAX_BORDER_TOWN_LEVEL)

    def upgrade(self) -> None:
        """
        Поднимает город на уровень выше, открывая еще один строительный слот.
        """
        self.assert_can_upgrade()
        self.level += 1

    # ==================================================================
    # ЗАСЕЛЕНИЕ СОЮЗНЫХ ЗЕМЕЛЬ
    # ==================================================================

    def assert_can_claim_land(self, coord: HexCoordinates) -> None:
        """
        Проверяет, годится ли гекс в союзные земли города, ничего не меняя.

        Земля должна вплотную примыкать к городу и умещаться в лимит:
        поселение кормится с того, что видно с его стен.
        """
        if hex_distance(coord, self.center_hex) != 1:
            raise HexNotAdjacentToTownError(self.name, hex_zone_id(coord))

        if len(self.claimed_hexes) >= MAX_BORDER_TOWN_ALLIED_LANDS:
            raise BorderTownMaxLandsReachedError(self.name, MAX_BORDER_TOWN_ALLIED_LANDS)

    def claim_land(self, coord: HexCoordinates) -> None:
        """
        Записывает смежный гекс в союзные земли города.

        Повторный выкуп той же земли - не ошибка, а ничего не меняющий
        приказ: город уже там.
        """
        if coord in self.claimed_hexes:
            return

        self.assert_can_claim_land(coord)
        self.claimed_hexes.append(coord)

    def release_zone(self, zone_id: str) -> None:
        """
        Убирает землю из владений города - например, когда ее отбил враг.
        """
        self.claimed_hexes = [
            coord for coord in self.claimed_hexes if hex_zone_id(coord) != zone_id
        ]

    # ==================================================================
    # УЧЕТ ВЛОЖЕНИЙ
    # ==================================================================

    def register_investment(self, costs: dict[ResourceType, float]) -> None:
        """
        Копит все траты фракции на город.

        Захватчик, разоривший поселение, получает долю именно от этой суммы,
        поэтому вложения считаются с первого дня, а не выводятся задним
        числом из уровня и числа земель.
        """
        for resource, amount in costs.items():
            self.invested_resources[resource] = (
                self.invested_resources.get(resource, 0.0) + amount
            )
