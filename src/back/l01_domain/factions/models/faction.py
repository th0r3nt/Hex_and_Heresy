"""
Faction - корневой агрегат одной политической стороны в партии.

Раса (race_id - каталог юнитов/зданий/лора) и фракция - разные вещи.
Внутри одной расы может быть несколько независимых Faction: например, у Баронских
войск сразу четыре соперничающих правителя (Медные Врата, Чёрные Топи,
Ржавая Корона, Кровавый Гребень), каждый со своим Lord, территорией и
дипломатией, но общим каталогом юнитов/зданий расы.
"""

from uuid import uuid4
from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.factions.models.buildings import Headquarters


class Faction(BaseModel):
    """
    Одна политическая сторона партии: игрок или ИИ, конкретный правитель,
    территория, экономика. 

    Дипломатические отношения сюда не встраиваются 
    - двусторонняя связь хранится в общем реестре уровня партии, 
    а не дублируется в каждом Faction.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    race_id: str = Field(
        ...,
        description="'humans' | 'greenskins' | 'elfs' | 'baronial_troops' | 'robbers' | 'mercenaries'",
    )
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

    def can_afford(self, resource: ResourceType, amount: float) -> bool:
        return self.resources.get(resource, 0.0) >= amount

    def spend(self, resource: ResourceType, amount: float) -> None:
        if not self.can_afford(resource, amount):
            raise ValueError(f"not enough {resource.value}")
        self.resources[resource] -= amount

    def earn(self, resource: ResourceType, amount: float) -> None:
        if amount < 0:
            raise ValueError("earned amount must be non-negative")
        self.resources[resource] = self.resources.get(resource, 0.0) + amount

    def gain_zone(self, zone_id: str) -> None:
        if zone_id not in self.controlled_zone_ids:
            self.controlled_zone_ids.append(zone_id)

    def lose_zone(self, zone_id: str) -> None:
        if zone_id in self.controlled_zone_ids:
            self.controlled_zone_ids.remove(zone_id)
