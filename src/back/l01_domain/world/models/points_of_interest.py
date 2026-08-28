"""
Точки интереса Ничьей земли: лорные ориентиры и процедурные аномалии,
которые делают нейтральные гексы неодинаковыми.

Точка интереса - это смысл гекса (что здесь произошло и что здесь можно
добыть). Она не путается с полем брани (BattlefieldLootSite): поле брани
рождается после конкретного тактического боя и держит конкретные трофеи,
а точка интереса стоит на карте с самого начала партии и лишь меняет
доходность добычи на своем гексе.

Пара "неизменяемый шаблон + размещенный экземпляр" повторяет уже принятую
в проекте связку Building / ConstructedBuilding.
"""

from enum import Enum
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.maps.models.strategic import HexCoordinates

# Множитель добычи по умолчанию: точка интереса ничего не меняет
NEUTRAL_YIELD_MULTIPLIER: float = 1.0


class PointOfInterestCategory(str, Enum):
    """
    Категория точки интереса - что это за место по своей природе.
    """

    BATTLEFIELD = "battlefield"  # застарелое поле брани, усеянное железом и костями
    GEO_ANOMALY = "geo_anomaly"  # резонитовая или тектоническая аномалия
    RUINS = "ruins"  # руины города, мануфактуры или крепости
    INFESTATION = "infestation"  # очаг заражения мицелием или мутацией
    BONEYARD = "boneyard"  # кладбище машин или гигантских тварей


# ==================================================================
# ШАБЛОН ИЗ КАТАЛОГА ГЕЙМДАТЫ
# ==================================================================


class PointOfInterestBlueprint(BaseModel):
    """
    Неизменяемое описание места из каталога геймдаты.

    Координат здесь нет: конкретный гекс выбирает генератор мира, потому
    что даже лорные ориентиры расставляются по сиду в пределах своего пояса.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="напр. poi_rusty_swords_valley")
    name: str = Field(..., min_length=1)
    category: PointOfInterestCategory = Field(...)
    lore_description: str = Field(default="")

    is_landmark: bool = Field(
        default=False,
        description=(
            "Лорный ориентир: место с именем и историей, которое существует "
            "в единственном экземпляре. Процедурные точки размножаются свободно"
        ),
    )

    yield_multipliers: dict[ResourceType, float] = Field(
        default_factory=dict,
        description="Множители добычи ресурсов на этом гексе (1.0 - обычная земля)",
    )
    race_yield_multipliers: dict[FactionRace, float] = Field(
        default_factory=dict,
        description=(
            "Расовая поправка к добыче поверх общей: эльфы качают резонит, "
            "а люди его не используют вовсе (множитель 0.0)"
        ),
    )
    morale_penalty_races: list[FactionRace] = Field(
        default_factory=list,
        description="Расы, чьи войска теряют боевой дух за работу в этом месте",
    )

    def build(self, hex_coordinates: HexCoordinates) -> "PointOfInterest":
        """
        Ставит место на конкретный гекс глобальной карты.
        """
        return PointOfInterest(blueprint=self, hex_coordinates=hex_coordinates)


# ==================================================================
# РАЗМЕЩЕННАЯ НА КАРТЕ ТОЧКА
# ==================================================================


class PointOfInterest(BaseModel):
    """
    Точка интереса, стоящая на конкретном гексе Ничьей земли.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    blueprint: PointOfInterestBlueprint = Field(...)
    hex_coordinates: HexCoordinates = Field(...)

    is_depleted: bool = Field(
        default=False, description="Место выработано и больше не дает бонуса к добыче"
    )

    @property
    def name(self) -> str:
        return self.blueprint.name

    @property
    def category(self) -> PointOfInterestCategory:
        return self.blueprint.category

    @property
    def lore_description(self) -> str:
        return self.blueprint.lore_description

    def yield_multiplier_for(
        self, resource: ResourceType, race: Optional[FactionRace] = None
    ) -> float:
        """
        Итоговый множитель добычи ресурса на этом гексе для конкретной расы.

        Общий множитель места умножается на расовую поправку: нулевая
        поправка означает, что раса не умеет пользоваться этим богатством
        (люди и резонит), и добыча падает до нуля.

        Поправка работает только по тем ресурсам, ради которых сюда и идут:
        на еду в резонитовом кратере не влияет ни раса, ни само место.
        Выработанное место не дает ничего сверх обычной земли.
        """
        if self.is_depleted:
            return NEUTRAL_YIELD_MULTIPLIER

        base = self.blueprint.yield_multipliers.get(resource)
        if base is None:
            return NEUTRAL_YIELD_MULTIPLIER
        if race is None:
            return base

        racial = self.blueprint.race_yield_multipliers.get(race, NEUTRAL_YIELD_MULTIPLIER)
        return base * racial

    def has_morale_penalty_for(self, race: FactionRace) -> bool:
        """
        Теряют ли войска этой расы боевой дух, работая в этом месте.
        """
        return race in self.blueprint.morale_penalty_races

    def deplete(self) -> None:
        """
        Помечает место выработанным.
        """
        self.is_depleted = True
