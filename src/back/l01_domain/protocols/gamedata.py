"""
Протокол репозитория статических данных игры.
"""

from typing import Optional, Protocol, runtime_checkable

from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.army.models.card.unit import UnitArchetype
from src.back.l01_domain.factions.models.buildings import Building


@runtime_checkable
class GameDataRepositoryProtocol(Protocol):
    """
    Контракт чтения статических данных игры из каталогов gamedata.
    """

    def get_unit_archetype(self, unit_id: str) -> Optional[UnitArchetype]: ...

    def get_equipment(self, equipment_id: str) -> Optional[Equipment]: ...

    def get_building(self, building_id: str) -> Optional[Building]: ...

    def list_faction_units(self, faction_id: str) -> list[UnitArchetype]: ...

    def list_faction_equipment(self, faction_id: str) -> list[Equipment]: ...

    def list_faction_buildings(self, faction_id: str) -> list[Building]: ...
