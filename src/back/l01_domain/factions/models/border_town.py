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

Здесь же лежит BorderTownOperation - то, что победитель делает с городом,
чей гарнизон выбит подчистую: разрушение, разграбление или захват. Операция
занимает несколько глобальных тактов, поэтому она не мгновенное действие, а
живущий в мире объект со своим обратным отсчетом.
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
    BORDER_TOWN_RESOLUTION_TICKS,
    BorderTownResolutionType,
    MAX_BORDER_TOWN_ALLIED_LANDS,
    MAX_BORDER_TOWN_LEVEL,
    MIN_BORDER_TOWN_LEVEL,
    ResourceType,
    border_town_resolution_loot,
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

    # ==================================================================
    # ПОСЛЕДСТВИЯ ПОРАЖЕНИЯ
    # ==================================================================

    def downgrade(self, levels: int) -> int:
        """
        Отбрасывает город на levels уровней вниз - последствие разграбления
        или захвата.

        Ниже первого уровня город не падает: даже разоренное поселение
        остается поселением, пока стоит хоть один дом. Возвращает, на сколько
        уровней город просел на самом деле.
        """
        if levels <= 0:
            return 0

        previous_level = self.level
        self.level = max(MIN_BORDER_TOWN_LEVEL, self.level - levels)
        return previous_level - self.level

    def transfer_ownership(self, new_faction_id: str) -> None:
        """
        Передает город новому хозяину.

        Земли и ратуши города перевешивает на нового владельца сервис: сам
        агрегат о списках фракций не знает и знать не должен.
        """
        self.faction_id = new_faction_id


# ==================================================================
# ОПЕРАЦИЯ НАД ПОБЕЖДЕННЫМ ГОРОДОМ
# ==================================================================


class BorderTownOperation(BaseModel):
    """
    Начатая победителем операция над городом: сожжение, разграбление
    или захват.

    Пока операция идет, армия захватчика стоит на гексе города и ничем
    другим не занята, а сам город не может ни отбиться, ни нанять войск.
    Эффект наступает разом в такте, когда отсчет доходит до нуля.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))

    town_id: str = Field(..., min_length=1, description="Город, над которым идет работа")
    army_id: str = Field(..., min_length=1, description="Армия победителя, занятая операцией")

    conqueror_faction_id: str = Field(..., min_length=1, description="Кто взял город")
    original_faction_id: str = Field(..., min_length=1, description="Кому город принадлежал")

    resolution_type: BorderTownResolutionType = Field(...)

    ticks_total: int = Field(..., ge=0, description="Сколько тактов операция длится всего")
    ticks_remaining: int = Field(..., ge=0, description="Сколько тактов осталось до эффекта")

    snapshot_invested_resources: dict[ResourceType, float] = Field(
        default_factory=dict,
        description=(
            "Снимок вложений города на момент начала операции. Считается один раз: "
            "добыча не должна меняться от того, что творится в городе эти два-три такта"
        ),
    )

    # ==================================================================
    # РАСЧЕТНЫЕ СВОЙСТВА
    # ==================================================================

    @property
    def loot(self) -> dict[ResourceType, float]:
        """Что достанется казне захватчика, когда операция завершится."""
        return border_town_resolution_loot(
            self.resolution_type, self.snapshot_invested_resources
        )

    @property
    def is_finished(self) -> bool:
        """Отсчет дошел до нуля - пора применять эффект."""
        return self.ticks_remaining <= 0

    # ==================================================================
    # ХОД ОПЕРАЦИИ
    # ==================================================================

    @classmethod
    def start(
        cls,
        town: "BorderTown",
        army_id: str,
        conqueror_faction_id: str,
        resolution_type: BorderTownResolutionType,
    ) -> "BorderTownOperation":
        """
        Заводит операцию над городом: длительность берется из таблицы, а
        вложения города тут же уходят в снимок.
        """
        ticks = BORDER_TOWN_RESOLUTION_TICKS.get(resolution_type, 0)
        return cls(
            town_id=town.id,
            army_id=army_id,
            conqueror_faction_id=conqueror_faction_id,
            original_faction_id=town.faction_id,
            resolution_type=resolution_type,
            ticks_total=ticks,
            ticks_remaining=ticks,
            snapshot_invested_resources=dict(town.invested_resources),
        )

    def advance(self) -> bool:
        """
        Прожигает один глобальный такт операции.

        Возвращает True, если после этого такта операцию пора применять.
        """
        if self.ticks_remaining > 0:
            self.ticks_remaining -= 1
        return self.is_finished
