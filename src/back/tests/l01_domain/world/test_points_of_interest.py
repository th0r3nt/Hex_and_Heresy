"""
Тесты для src/back/l01_domain/world/models/points_of_interest.py

Точка интереса меняет доходность своего гекса, и делает это по-разному
для разных рас: резонит для эльфов - материал, для людей - ничто.
"""

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.points_of_interest import (
    PointOfInterest,
    PointOfInterestBlueprint,
    PointOfInterestCategory,
)
from src.back.l01_domain.world.models.state import WorldState


def _crater_blueprint() -> PointOfInterestBlueprint:
    return PointOfInterestBlueprint(
        id="poi_test_crater",
        name="Кратер сияния",
        category=PointOfInterestCategory.GEO_ANOMALY,
        is_landmark=True,
        lore_description="Зеленое бритвенно-острое стекло.",
        yield_multipliers={ResourceType.MATERIAL: 3.0},
        race_yield_multipliers={
            FactionRace.ELFS: 1.5,
            FactionRace.HUMANS: 0.0,
        },
        morale_penalty_races=[FactionRace.HUMANS],
    )


class TestPointOfInterest:
    def test_build_places_blueprint_on_hex(self):
        coord = HexCoordinates.from_axial(2, -1)

        poi = _crater_blueprint().build(coord)

        assert isinstance(poi, PointOfInterest)
        assert poi.hex_coordinates == coord
        assert poi.name == "Кратер сияния"
        assert poi.category == PointOfInterestCategory.GEO_ANOMALY
        assert poi.lore_description == "Зеленое бритвенно-острое стекло."
        assert not poi.is_depleted

    def test_race_multiplier_stacks_on_top_of_common_one(self):
        poi = _crater_blueprint().build(HexCoordinates.from_axial(0, 0))

        assert poi.yield_multiplier_for(ResourceType.MATERIAL) == 3.0
        assert poi.yield_multiplier_for(ResourceType.MATERIAL, FactionRace.ELFS) == 4.5

    def test_race_that_cannot_use_the_resource_gets_nothing(self):
        """Люди резонит не используют: множитель 0.0 обнуляет всю добычу."""
        poi = _crater_blueprint().build(HexCoordinates.from_axial(0, 0))

        assert poi.yield_multiplier_for(ResourceType.MATERIAL, FactionRace.HUMANS) == 0.0

    def test_race_without_own_multiplier_gets_common_one(self):
        poi = _crater_blueprint().build(HexCoordinates.from_axial(0, 0))

        assert poi.yield_multiplier_for(ResourceType.MATERIAL, FactionRace.GREENSKINS) == 3.0

    def test_resource_not_listed_in_blueprint_is_ordinary_land(self):
        poi = _crater_blueprint().build(HexCoordinates.from_axial(0, 0))

        assert poi.yield_multiplier_for(ResourceType.FOOD, FactionRace.ELFS) == 1.0

    def test_depleted_place_gives_no_bonus_at_all(self):
        poi = _crater_blueprint().build(HexCoordinates.from_axial(0, 0))

        poi.deplete()

        assert poi.is_depleted
        assert poi.yield_multiplier_for(ResourceType.MATERIAL, FactionRace.ELFS) == 1.0

    def test_morale_penalty_applies_only_to_listed_races(self):
        poi = _crater_blueprint().build(HexCoordinates.from_axial(0, 0))

        assert poi.has_morale_penalty_for(FactionRace.HUMANS)
        assert not poi.has_morale_penalty_for(FactionRace.ELFS)


class TestWorldStatePointsOfInterest:
    def test_world_state_registers_and_finds_place_by_hex(self):
        world = WorldState()
        coord = HexCoordinates.from_axial(-3, 1)
        poi = _crater_blueprint().build(coord)

        world.add_point_of_interest(poi)

        assert world.points_of_interest[poi.id] is poi
        assert world.get_point_of_interest_at(coord) is poi
        assert world.get_point_of_interest_at(HexCoordinates.from_axial(5, 5)) is None
