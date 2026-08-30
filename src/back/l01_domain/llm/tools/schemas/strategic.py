"""
Схемы параметров инструментов глобальной стратегической карты.
"""

from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import (
    MAX_TAX_RATE,
    MIN_TAX_RATE,
    BorderTownResolutionType,
)
from src.back.l01_domain.maps.models.strategic import HexCoordinates


class OrderArmyMarchParams(BaseModel):
    """Параметры приказа на марш армии."""

    army_id: str = Field(..., min_length=1, description="Идентификатор выступающей армии")
    target_q: int = Field(..., description="Осевая координата Q целевого гекса")
    target_r: int = Field(..., description="Осевая координата R целевого гекса")

    def to_target_hex(self) -> HexCoordinates:
        return HexCoordinates.from_axial(self.target_q, self.target_r)


class SetTaxRateParams(BaseModel):
    """Параметры изменения ставки налога."""

    rate: float = Field(
        ...,
        ge=MIN_TAX_RATE,
        le=MAX_TAX_RATE,
        description=f"Новая ставка налога в диапазоне [{MIN_TAX_RATE}, {MAX_TAX_RATE}]",
    )


class AssignWorkerParams(BaseModel):
    """Параметры назначения отряда рабочих на здание."""

    squad_id: str = Field(
        ..., min_length=1, description="Идентификатор отряда рабочих тира 00"
    )
    building_id: str = Field(..., min_length=1, description="Идентификатор целевого здания")


class UnassignWorkerParams(BaseModel):
    """Параметры снятия рабочих со стационарного здания."""

    squad_id: str = Field(..., min_length=1, description="Идентификатор отряда рабочих")


class DispatchExpeditionParams(BaseModel):
    """Параметры отправки каравана рабочих в экспедицию."""

    squad_id: str = Field(..., min_length=1, description="Идентификатор отряда рабочих")
    target_q: int = Field(..., description="Координата Q нейтрального гекса добычи")
    target_r: int = Field(..., description="Координата R нейтрального гекса добычи")
    home_q: int = Field(..., description="Координата Q базы для возвращения")
    home_r: int = Field(..., description="Координата R базы для возвращения")
    mining_duration_ticks: int = Field(
        default=3, ge=1, description="Длительность добычи на нейтральном гексе в тактах"
    )

    def to_target_hex(self) -> HexCoordinates:
        return HexCoordinates.from_axial(self.target_q, self.target_r)

    def to_home_hex(self) -> HexCoordinates:
        return HexCoordinates.from_axial(self.home_q, self.home_r)


class FoundBorderTownParams(BaseModel):
    """Параметры основания пограничного города."""

    name: str = Field(..., min_length=1, description="Название нового пограничного города")
    target_q: int = Field(..., description="Координата Q свободного гекса")
    target_r: int = Field(..., description="Координата R свободного гекса")

    def to_target_hex(self) -> HexCoordinates:
        return HexCoordinates.from_axial(self.target_q, self.target_r)


class UpgradeBorderTownParams(BaseModel):
    """Параметры улучшения пограничного города."""

    town_id: str = Field(..., min_length=1, description="Идентификатор улучшаемого города")


class ClaimBorderLandParams(BaseModel):
    """Параметры выкупа смежной земли для города."""

    town_id: str = Field(..., min_length=1, description="Идентификатор пограничного города")
    target_q: int = Field(..., description="Координата Q смежного свободного гекса")
    target_r: int = Field(..., description="Координата R смежного свободного гекса")

    def to_target_hex(self) -> HexCoordinates:
        return HexCoordinates.from_axial(self.target_q, self.target_r)


class ResolveBorderTownParams(BaseModel):
    """Параметры решения судьбы побежденного города."""

    town_id: str = Field(..., min_length=1, description="Идентификатор побежденного города")
    army_id: str = Field(..., min_length=1, description="Идентификатор армии победителя")
    resolution_type: BorderTownResolutionType = Field(
        ..., description="Тип решения: raze, pillage, occupy, ignore"
    )


class StationSquadParams(BaseModel):
    """Параметры расквартирования отряда в гарнизон."""

    army_id: str = Field(..., min_length=1, description="Идентификатор исходной армии")
    squad_id: str = Field(..., min_length=1, description="Идентификатор отряда")
    zone_id: str = Field(..., min_length=1, description="Идентификатор земли гарнизона")


class UnstationSquadParams(BaseModel):
    """Параметры вывода отряда из гарнизона в армию."""

    army_id: str = Field(..., min_length=1, description="Идентификатор принимающей армии")
    squad_id: str = Field(..., min_length=1, description="Идентификатор отряда")
    zone_id: str = Field(..., min_length=1, description="Идентификатор земли гарнизона")
