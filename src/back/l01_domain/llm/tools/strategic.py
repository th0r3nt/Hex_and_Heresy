"""
Инструменты глобальной стратегической карты.
"""

from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import (
    MAX_TAX_RATE,
    MIN_TAX_RATE,
    BorderTownResolutionType,
)
from src.back.l01_domain.llm.models.skills import ToolDefinition
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


ORDER_ARMY_MARCH = ToolDefinition(
    name="order_army_march",
    description="Приказать армии начать марш к указанному гексу на глобальной карте.",
    parameters_model=OrderArmyMarchParams,
)

SET_TAX_RATE = ToolDefinition(
    name="set_tax_rate",
    description="Установить новую налоговую ставку для фракции.",
    parameters_model=SetTaxRateParams,
)

ASSIGN_WORKER = ToolDefinition(
    name="assign_worker",
    description="Назначить отряд рабочих на экономическое здание для стационарной добычи.",
    parameters_model=AssignWorkerParams,
)

UNASSIGN_WORKER = ToolDefinition(
    name="unassign_worker",
    description="Снять отряд рабочих с экономического здания.",
    parameters_model=UnassignWorkerParams,
)

DISPATCH_EXPEDITION = ToolDefinition(
    name="dispatch_expedition",
    description="Отправить караван рабочих в экспедицию на нейтральный гекс за ресурсами.",
    parameters_model=DispatchExpeditionParams,
)

FOUND_BORDER_TOWN = ToolDefinition(
    name="found_border_town",
    description="Основать новый пограничный город на свободном нейтральном гексе.",
    parameters_model=FoundBorderTownParams,
)

UPGRADE_BORDER_TOWN = ToolDefinition(
    name="upgrade_border_town",
    description="Улучшить пограничный город на следующий уровень развития.",
    parameters_model=UpgradeBorderTownParams,
)

CLAIM_BORDER_LAND = ToolDefinition(
    name="claim_border_land",
    description="Выкупить смежный нейтральный гекс в качестве союзной земли пограничного города.",
    parameters_model=ClaimBorderLandParams,
)

RESOLVE_BORDER_TOWN = ToolDefinition(
    name="resolve_border_town",
    description="Решить судьбу побежденного пограничного города (сжечь, разграбить, занять или пропустить).",
    parameters_model=ResolveBorderTownParams,
)

STATION_SQUAD = ToolDefinition(
    name="station_squad",
    description="Расквартировать отряд регулярной армии в гарнизон земли за крепостные стены.",
    parameters_model=StationSquadParams,
)

UNSTATION_SQUAD = ToolDefinition(
    name="unstation_squad",
    description="Вывести отряд из гарнизона крепостных стен обратно в полевую армию.",
    parameters_model=UnstationSquadParams,
)
