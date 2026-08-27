"""
Faction - корневой агрегат одной политической стороны в партии.
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions.factions import (
    InsufficientResourcesError,
    InvalidTaxRateError,
    NegativeResourceAmountError,
)
from src.back.l01_domain.factions.constants import (
    BASE_TAX_HQ_PER_LEVEL,
    BASE_TAX_RATE,
    BASE_TAX_ZONE_PER_LEVEL,
    MAX_TAX_RATE,
    MIN_TAX_RATE,
    ResourceType,
    TaxBandEffects,
    TaxPolicyBand,
    resolve_tax_band,
)
from src.back.l01_domain.factions.models.buildings import (
    ConstructedBuilding,
    Headquarters,
    RegionalHall,
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

    regional_halls: list[RegionalHall] = Field(
        default_factory=list,
        description="Ратуши союзных земель - административные центры и база налогообложения",
    )

    tax_rate: float = Field(
        default=BASE_TAX_RATE,
        description=(
            "Ставка налога ползунком от 0.0 (каникулы) до 2.0 (грабеж). "
            "Множитель к подушному сбору с цитадели и ратуш"
        ),
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

    @field_validator("tax_rate")
    @classmethod
    def validate_tax_rate(cls, rate: float) -> float:
        """
        Держит ставку в границах ползунка - в том числе при загрузке сохранения.
        """
        if rate < MIN_TAX_RATE or rate > MAX_TAX_RATE:
            raise InvalidTaxRateError(rate=rate, min_rate=MIN_TAX_RATE, max_rate=MAX_TAX_RATE)
        return rate

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
        self._require(resource, amount)
        self.resources[resource] -= amount

    def spend_all(self, costs: dict[ResourceType, float]) -> None:
        """
        Списывает набор ресурсов разом.

        Покупка неделима: не хватило хотя бы одного ресурса - казна остается
        нетронутой целиком. Иначе игрок платил бы золотом за предмет, которого
        так и не получит из-за нехватки материалов.

        Ошибка называет первый ресурс, которого не хватило, в порядке costs.
        """
        for resource, amount in costs.items():
            self._require(resource, amount)

        for resource, amount in costs.items():
            self.resources[resource] -= amount

    def _require(self, resource: ResourceType, amount: float) -> None:
        """Убеждается, что ресурса хватает, или роняет доменную ошибку."""
        if not self.can_afford(resource, amount):
            raise InsufficientResourcesError(
                resource=resource.value,
                required=amount,
                available=self.resources.get(resource, 0.0),
                faction_id=self.id,
            )

    def earn(self, resource: ResourceType, amount: float) -> None:
        """
        Начисляет ресурс в казну.
        """
        if amount < 0:
            raise NegativeResourceAmountError(amount=amount, operation="earn")
        self.resources[resource] = self.resources.get(resource, 0.0) + amount

    # ====================================================
    # Налоги
    # ====================================================

    @property
    def tax_effects(self) -> TaxBandEffects:
        """Последствия текущей ставки: мораль, забастовки и риск бунта."""
        return resolve_tax_band(self.tax_rate)

    @property
    def tax_band(self) -> TaxPolicyBand:
        """Режим налогообложения, в который попадает текущая ставка."""
        return self.tax_effects.band

    @property
    def taxable_base_gold(self) -> float:
        """
        Налогооблагаемая база за такт при ставке 1.0: подушный сбор с цитадели
        плюс сбор с периферии за каждую союзную ратушу.
        """
        hq_base = self.headquarters.level * BASE_TAX_HQ_PER_LEVEL
        zones_base = sum(hall.level * BASE_TAX_ZONE_PER_LEVEL for hall in self.regional_halls)
        return hq_base + zones_base

    @property
    def tax_income_gold(self) -> float:
        """Сбор золота за такт с учетом выставленной ставки."""
        return self.taxable_base_gold * self.tax_rate

    def set_tax_rate(self, rate: float) -> None:
        """
        Двигает ползунок налога. Ставка вне [0.0, 2.0] - доменная ошибка.
        """
        self.tax_rate = self.validate_tax_rate(rate)

    # ====================================================
    # Территория и здания
    # ====================================================

    def add_regional_hall(self, hall: RegionalHall) -> None:
        """
        Ставит ратушу в союзной земле. На зону приходится ровно одна ратуша.
        """
        if any(existing.zone_id == hall.zone_id for existing in self.regional_halls):
            return
        self.regional_halls.append(hall)

    def get_regional_hall(self, zone_id: str) -> Optional[RegionalHall]:
        """Возвращает ратушу союзной земли, если она там стоит."""
        return next((h for h in self.regional_halls if h.zone_id == zone_id), None)

    def gain_zone(self, zone_id: str) -> None:
        """
        Берет союзную зону под контроль.
        """
        if zone_id not in self.controlled_zone_ids:
            self.controlled_zone_ids.append(zone_id)

    def lose_zone(self, zone_id: str) -> None:
        """
        Теряет контроль над зоной вместе со стоящей там ратушей: с чужой
        земли налог не собрать.
        """
        if zone_id in self.controlled_zone_ids:
            self.controlled_zone_ids.remove(zone_id)
        self.regional_halls = [h for h in self.regional_halls if h.zone_id != zone_id]

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
