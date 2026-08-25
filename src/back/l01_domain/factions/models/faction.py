"""
Faction - корневой агрегат одной политической стороны в партии.
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions.factions import (
    InsufficientResourcesError,
    NegativeResourceAmountError,
)
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.buildings import (
    ConstructedBuilding,
    Headquarters,
)
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.maps.models.strategic import HexCoordinates


class Faction(BaseModel):
    """
    Одна политическая сторона партии: игрок или ИИ, конкретный правитель,
    территория, здания и экономика.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    race: FactionRace = Field(..., description="Расовая принадлежность фракции")
    name: str = Field(
        ..., min_length=1, description="Имя конкретной фракции в партии, не расы"
    )
    is_player_controlled: bool = Field(default=False)

    lord: Lord = Field(...)
    headquarters: Headquarters = Field(...)

    resources: dict[ResourceType, float] = Field(
        default_factory=lambda: {resource: 0.0 for resource in ResourceType}
    )

    controlled_zone_ids: list[str] = Field(
        default_factory=list, description="ID гексов союзных земель под контролем"
    )

    capital_hex: Optional[HexCoordinates] = Field(
        default=None,
        description=(
            "Гекс главного здания фракции."
        ),
    )

    buildings: list[ConstructedBuilding] = Field(
        default_factory=list, description="Список возведенных и строящихся зданий"
    )

    @property
    def race_id(self) -> str:
        """Строковый идентификатор расы для обратной совместимости."""
        return self.race.value

    def can_afford(self, resource: ResourceType, amount: float) -> bool:
        """
        Проверяет наличие достаточного объема ресурса.
        """
        return self.resources.get(resource, 0.0) >= amount

    def spend(self, resource: ResourceType, amount: float) -> None:
        """
        Списывает указанный объем ресурса.
        """
        if not self.can_afford(resource, amount):
            raise InsufficientResourcesError(
                resource=resource.value,
                required=amount,
                available=self.resources.get(resource, 0.0),
                faction_id=self.id,
            )
        self.resources[resource] -= amount

    def earn(self, resource: ResourceType, amount: float) -> None:
        """
        Начисляет ресурс в казну.
        """
        if amount < 0:
            raise NegativeResourceAmountError(amount=amount, operation="earn")
        self.resources[resource] = self.resources.get(resource, 0.0) + amount

    def gain_zone(self, zone_id: str) -> None:
        """
        Берет союзную зону под контроль.
        """
        if zone_id not in self.controlled_zone_ids:
            self.controlled_zone_ids.append(zone_id)

    def lose_zone(self, zone_id: str) -> None:
        """
        Теряет контроль над зоной.
        """
        if zone_id in self.controlled_zone_ids:
            self.controlled_zone_ids.remove(zone_id)

    def add_building(self, building: ConstructedBuilding) -> None:
        """
        Регистрирует построенное или строящееся здание.
        """
        self.buildings.append(building)

    def remove_building(self, building_id: str) -> Optional[ConstructedBuilding]:
        """
        Удаляет здание по идентификатору.
        """
        for i, b in enumerate(self.buildings):
            if b.id == building_id:
                return self.buildings.pop(i)
        return None
