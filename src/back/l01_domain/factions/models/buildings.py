"""
Здания фракции: неизменяемые шаблоны (Building, BuildingUpgrade) и
"центры управления" зоны (Headquarters, RegionalHall), которые дают
строительные слоты. Мутируемый построенный экземпляр - ConstructedBuilding.
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.common import MechanicalModifier
from src.back.l01_domain.maps.constants import TerritoryZoneType
from src.back.l01_domain.factions.constants import (
    ResourceType,
    BuildingCategory,
    MIN_HQ_LEVEL,
    MAX_HQ_LEVEL,
    HQ_BASE_BUILDING_SLOTS,
    HQ_BUILDING_SLOTS_PER_LEVEL,
    MIN_TOWNHALL_LEVEL,
    MAX_TOWNHALL_LEVEL,
    TOWNHALL_BASE_BUILDING_SLOTS,
    TOWNHALL_BUILDING_SLOTS_PER_LEVEL,
    TOWNHALL_MAX_BUILDING_SLOTS,
    MIN_BUILDING_UNLOCK_TIER,
    MAX_BUILDING_UNLOCK_TIER,
)

from src.back.l01_domain.exceptions.factions import BuildingMaxLevelReachedError


class BuildingUpgrade(BaseModel):
    """
    Улучшение здания. Не занимает отдельный слот
    - пристраивается к уже построенному зданию.
    (см. building.md).
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    lore_description: str = Field(default="")

    cost_gold: float = Field(default=0.0, ge=0)
    cost_material: float = Field(default=0.0, ge=0)

    modifiers: list[MechanicalModifier] = Field(default_factory=list)


class Building(BaseModel):
    """
    Неизменяемый шаблон здания, занимающего один строительный слот
    (экономическое/военное/оборонительное/уникальное).
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="напр. baronial_building_oppressed_village")
    faction_id: str = Field(..., description="К какой расе/гейм-каталогу принадлежит")

    name: str = Field(..., min_length=1)
    lore_description: str = Field(default="")

    category: BuildingCategory = Field(...)
    allowed_zone: TerritoryZoneType = Field(...)

    cost_gold: float = Field(default=0.0, ge=0)
    cost_material: float = Field(default=0.0, ge=0)

    construction_ticks: int = Field(default=1, ge=1)  # Время постройки

    requires_workers: bool = Field(
        default=False,
        description="Нужны ли назначенные рабочие для производства (см. economy.md)",
    )
    resource_output_per_worker: dict[ResourceType, float] = Field(default_factory=dict)

    unlocked_unit_ids: list[str] = Field(
        default_factory=list, description="ID UnitArchetype, если здание открывает найм"
    )
    unlocked_equipment_ids: list[str] = Field(
        default_factory=list, description="ID Equipment, если открывает новый арсенал"
    )
    unlock_tier: Optional[int] = Field(
        default=None, ge=MIN_BUILDING_UNLOCK_TIER, le=MAX_BUILDING_UNLOCK_TIER
    )  # На каком тире будет доступна постройка

    vision_radius_hexes: int = Field(
        default=0,
        ge=0,
        description=(
            "Радиус обзора, который здание снимает с тумана войны вокруг своего "
            "гекса. Ноль - здание не смотрит наружу; смотрят только вышки, "
            "обсерватории и прочая наблюдательная застройка"
        ),
    )

    available_upgrades: list[BuildingUpgrade] = Field(default_factory=list)
    special_rules: Optional[str] = Field(default=None)


class Headquarters(BaseModel):
    """
    Главное здание фракции - ровно одно на фракцию, стоит на главном гексе.
    Уничтожение означает конец игры для владельца.
    """

    faction_id: str = Field(...)
    name: str = Field(
        ..., description="Расово-специфичное название - 'Цитадель', 'Шатёр вождя' и т.д."
    )
    level: int = Field(default=1, ge=MIN_HQ_LEVEL, le=MAX_HQ_LEVEL)

    is_destroyed: bool = Field(
        default=False,
        description=(
            "Цитадель взята штурмом и сожжена. Отстроить ее нельзя: фракция "
            "с павшей цитаделью выбывает из партии"
        ),
    )

    @property
    def building_slots(self) -> int:
        return HQ_BASE_BUILDING_SLOTS + max(0, self.level - 1) * HQ_BUILDING_SLOTS_PER_LEVEL

    def upgrade(self) -> None:
        if self.level >= MAX_HQ_LEVEL:
            raise BuildingMaxLevelReachedError(self.name, MAX_HQ_LEVEL)
        self.level += 1

    def destroy(self) -> None:
        """
        Отмечает падение цитадели - конец игры для ее владельца.

        Само по себе это только флаг: выводы из него делает проверка
        глобальных целей партии (см. VictoryEvaluator).
        """
        self.is_destroyed = True


class RegionalHall(BaseModel):
    """
    Ратуша/место управления - местный центр управления
    союзной землёй. По одному на гекс союзных земель.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    faction_id: str = Field(...)
    zone_id: str = Field(
        ..., description="ID гекса союзных земель (см. будущий maps/models/global.py)"
    )
    name: str = Field(...)
    level: int = Field(default=1, ge=MIN_TOWNHALL_LEVEL, le=MAX_TOWNHALL_LEVEL)

    @property
    def building_slots(self) -> int:
        raw = (
            TOWNHALL_BASE_BUILDING_SLOTS
            + max(0, self.level - 1) * TOWNHALL_BUILDING_SLOTS_PER_LEVEL
        )
        return min(raw, TOWNHALL_MAX_BUILDING_SLOTS)

    def upgrade(self) -> None:
        if self.level >= MAX_TOWNHALL_LEVEL:
            raise BuildingMaxLevelReachedError(self.name, MAX_TOWNHALL_LEVEL)
        self.level += 1


class ConstructedBuilding(BaseModel):
    """
    Конкретный построенный экземпляр здания в игре - мутируемое
    состояние поверх неизменяемого шаблона Building.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    building: Building = Field(...)
    zone_id: str = Field(...)

    active_upgrades: list[BuildingUpgrade] = Field(default_factory=list)
    is_under_construction: bool = Field(default=True)
    construction_ticks_remaining: int = Field(default=0, ge=0)

    assigned_worker_squad_ids: list[str] = Field(default_factory=list)

    @property
    def vision_radius_hexes(self) -> int:
        """
        Радиус обзора, который дает уже работающее здание.

        Стройплощадка не смотрит никуда: пока вышка не достроена, наверх
        некому подняться.
        """
        if self.is_under_construction:
            return 0
        return self.building.vision_radius_hexes

    def apply_upgrade(self, upgrade: BuildingUpgrade) -> None:
        if any(u.id == upgrade.id for u in self.active_upgrades):
            return
        self.active_upgrades.append(upgrade)

    def complete_construction(self) -> None:
        self.is_under_construction = False
        self.construction_ticks_remaining = 0
