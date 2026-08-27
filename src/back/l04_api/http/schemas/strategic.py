"""
Схемы приказов глобальной карты: марш армий, рабочие и экспедиции.
"""

from pydantic import BaseModel, Field

from src.back.l01_domain.maps.models.strategic import HexCoordinates


class MarchOrderRequest(BaseModel):
    """
    Приказ армии выдвинуться к гексу. Сам марш считается глобальным тактом.
    """

    target_hex: HexCoordinates = Field(...)


class MarchOrderResponse(BaseModel):
    """
    Проложенный маршрут: интерфейс рисует его пунктиром на карте.
    """

    army_id: str = Field(...)
    planned_path: list[HexCoordinates] = Field(default_factory=list)


class WorkerAssignRequest(BaseModel):
    """
    Назначение отряда рабочих на экономическое здание.
    """

    squad_id: str = Field(..., min_length=1)
    faction_id: str = Field(..., min_length=1)
    building_id: str = Field(..., min_length=1)


class ExpeditionRequest(BaseModel):
    """
    Отправка каравана рабочих на нейтральный гекс.
    """

    squad_id: str = Field(..., min_length=1)
    faction_id: str = Field(..., min_length=1)
    target_hex: HexCoordinates = Field(...)
    home_hex: HexCoordinates = Field(...)
    mining_duration_ticks: int = Field(default=3, ge=1)
