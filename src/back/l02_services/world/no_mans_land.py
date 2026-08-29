"""
Наполнение Ничьей земли: свободные нейтральные гексы, лорные ориентиры
экваториального пояса, процедурные точки интереса и застарелые поля брани
под ориентирами-побоищами.

Все выборы гексов идут через жребий партии, поэтому множества здесь нигде не
перебираются напрямую: порядок обхода множества в Python зависит от хэшей, и
один и тот же сид давал бы разные карты от запуска к запуску.
"""

from random import Random
from typing import Iterable

from src.back.l01_domain.maps.constants import TerritoryZoneType
from src.back.l01_domain.maps.models.strategic import (
    HexCoordinates,
    determine_zone_type,
    generate_standard_map_coordinates,
)
from src.back.l01_domain.protocols.gamedata import GameDataRepositoryProtocol
from src.back.l01_domain.world.constants import (
    LANDMARK_BATTLEFIELD_RESONITE_RANGE,
    NO_MANS_LAND_LANDMARK_BELT_RADIUS,
    PROCEDURAL_POI_DENSITY_RANGE,
)
from src.back.l01_domain.world.models.battleground import BattlefieldLootSite
from src.back.l01_domain.world.models.points_of_interest import (
    PointOfInterestBlueprint,
    PointOfInterestCategory,
)
from src.back.l01_domain.world.models.state import WorldState


class NoMansLandPopulator:
    """
    Раскладывает по нейтральным землям все, что делает их неодинаковыми.
    """

    def __init__(self, gamedata: GameDataRepositoryProtocol) -> None:
        self._gamedata = gamedata

    # ==================================================================
    # НАПОЛНЕНИЕ ЦЕЛИКОМ
    # ==================================================================

    def populate(self, world: WorldState, rng: Random) -> None:
        """
        Считает свободные гексы, разводит по ним лорные ориентиры и рассыпает
        процедурные места.
        """
        world.neutral_hexes = self._collect_neutral_hexes(world)

        free_hexes = set(world.neutral_hexes)
        self._place_landmarks(world, free_hexes, rng)
        self._scatter_procedural_points(world, free_hexes, rng)

    @staticmethod
    def _collect_neutral_hexes(world: WorldState) -> list[HexCoordinates]:
        """
        Гексы Ничьей земли: все, что не является цитаделью или ее лепестком.

        Лепестки считаются занятыми целиком, даже те, которые сторона еще не
        обжила: рано или поздно они станут ее союзными землями.
        """
        bases = [
            faction.capital_hex
            for faction in world.factions.values()
            if faction.capital_hex is not None
        ]

        return [
            coord
            for coord in generate_standard_map_coordinates()
            if determine_zone_type(coord, bases) == TerritoryZoneType.NEUTRAL_LANDS
        ]

    # ==================================================================
    # ТОЧКИ ИНТЕРЕСА
    # ==================================================================

    def _place_landmarks(
        self, world: WorldState, free_hexes: set[HexCoordinates], rng: Random
    ) -> None:
        """
        Разводит лорные ориентиры по экваториальному поясу Ничьей земли.

        Каждый ориентир уникален и существует ровно в одном экземпляре,
        поэтому гексы под них выбираются без повторов.
        """
        belt = self._ordered(
            coord
            for coord in free_hexes
            if abs(coord.r) <= NO_MANS_LAND_LANDMARK_BELT_RADIUS
        )
        landmarks = sorted(
            self._gamedata.list_landmark_points_of_interest(), key=lambda bp: bp.id
        )
        if not belt or not landmarks:
            return

        chosen = rng.sample(belt, k=min(len(landmarks), len(belt)))

        for blueprint, coord in zip(landmarks, chosen):
            world.add_point_of_interest(blueprint.build(coord))
            free_hexes.discard(coord)

            if blueprint.category == PointOfInterestCategory.BATTLEFIELD:
                world.add_battlefield_site(
                    self._build_ancient_battlefield(blueprint, coord, rng)
                )

    def _scatter_procedural_points(
        self, world: WorldState, free_hexes: set[HexCoordinates], rng: Random
    ) -> None:
        """
        Рассыпает малые точки интереса по оставшимся нейтральным гексам.

        Плотность выбирает сам сид партии: один мир выходит богаче другого,
        но оба воспроизводимы.
        """
        blueprints = sorted(
            self._gamedata.list_procedural_points_of_interest(), key=lambda bp: bp.id
        )
        candidates = self._ordered(free_hexes)
        if not blueprints or not candidates:
            return

        density = rng.uniform(*PROCEDURAL_POI_DENSITY_RANGE)
        count = min(len(candidates), int(len(candidates) * density))

        for coord in rng.sample(candidates, k=count):
            world.add_point_of_interest(rng.choice(blueprints).build(coord))
            free_hexes.discard(coord)

    # ==================================================================
    # ЗАСТАРЕЛЫЕ ПОЛЯ БРАНИ
    # ==================================================================

    @staticmethod
    def _build_ancient_battlefield(
        blueprint: PointOfInterestBlueprint, coord: HexCoordinates, rng: Random
    ) -> BattlefieldLootSite:
        """
        Ставит на ориентир застарелое поле брани.

        Такое поле нетленно: оно стоит на карте с самого начала партии и
        таймеру гниения не подчиняется. Железо с него давно растащили
        мародеры, а вот резонит из пропитанной кровью земли еще качают.
        """
        low, high = LANDMARK_BATTLEFIELD_RESONITE_RANGE
        return BattlefieldLootSite(
            hex_coordinates=coord,
            origin_battle_id=blueprint.id,
            residual_resonite=round(rng.uniform(low, high), 1),
            is_imperishable=True,
        )

    # ==================================================================
    # ВСПОМОГАТЕЛЬНОЕ
    # ==================================================================

    @staticmethod
    def _ordered(hexes: Iterable[HexCoordinates]) -> list[HexCoordinates]:
        """
        Приводит гексы к устойчивому порядку перед жеребьевкой.
        """
        return sorted(hexes, key=lambda coord: (coord.r, coord.q))
