"""
Протокол репозитория статических данных игры.
"""

from typing import Optional, Protocol, runtime_checkable

from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.army.models.card.roster import RosterEntry
from src.back.l01_domain.army.models.card.unit import UnitArchetype
from src.back.l01_domain.factions.models.buildings import Building
from src.back.l01_domain.factions.models.legendary import (
    LegendaryCommanderTemplate,
    LegendaryHeroTemplate,
    LegendaryLordTemplate,
)
from src.back.l01_domain.world.models.points_of_interest import PointOfInterestBlueprint


@runtime_checkable
class GameDataRepositoryProtocol(Protocol):
    """
    Контракт чтения статических данных игры из каталогов gamedata.
    """

    # ====================================================
    # Карточки: юниты, снаряжение, здания
    # ====================================================

    def get_unit_archetype(self, unit_id: str) -> Optional[UnitArchetype]: ...

    def get_equipment(self, equipment_id: str) -> Optional[Equipment]: ...

    def get_building(self, building_id: str) -> Optional[Building]: ...

    def list_faction_units(self, faction_id: str) -> list[UnitArchetype]: ...

    def list_faction_equipment(self, faction_id: str) -> list[Equipment]: ...

    def list_faction_buildings(self, faction_id: str) -> list[Building]: ...

    # ====================================================
    # Ростер: готовые рецепты найма отрядов
    # ====================================================

    def get_roster_entry(self, roster_id: str) -> Optional[RosterEntry]: ...

    def list_faction_roster(self, faction_id: str) -> list[RosterEntry]: ...

    # ====================================================
    # Легендарные личности
    # ====================================================

    def get_legendary_lord(self, lord_id: str) -> Optional[LegendaryLordTemplate]: ...

    def get_legendary_commander(
        self, commander_id: str
    ) -> Optional[LegendaryCommanderTemplate]: ...

    def get_legendary_hero(self, hero_id: str) -> Optional[LegendaryHeroTemplate]: ...

    def list_faction_legendary_lords(
        self, faction_id: str
    ) -> list[LegendaryLordTemplate]: ...

    def list_faction_legendary_commanders(
        self, faction_id: str
    ) -> list[LegendaryCommanderTemplate]: ...

    def list_faction_legendary_heroes(
        self, faction_id: str
    ) -> list[LegendaryHeroTemplate]: ...

    # ====================================================
    # Точки интереса Ничьей земли
    # ====================================================

    def get_point_of_interest(self, poi_id: str) -> Optional[PointOfInterestBlueprint]: ...

    def list_landmark_points_of_interest(self) -> list[PointOfInterestBlueprint]: ...

    def list_procedural_points_of_interest(self) -> list[PointOfInterestBlueprint]: ...
