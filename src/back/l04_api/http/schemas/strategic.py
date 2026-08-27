"""
Схемы приказов глобальной карты: марш армий, рабочие и экспедиции.
"""

from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import (
    MAX_TAX_RATE,
    MIN_TAX_RATE,
    TaxPolicyBand,
)
from src.back.l01_domain.factions.models.faction import Faction
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


# ====================================================
# Налоги
# ====================================================


class SetTaxRateRequest(BaseModel):
    """
    Новое положение налогового ползунка от 0.0 до 2.0.
    """

    rate: float = Field(..., description=f"Ставка налога [{MIN_TAX_RATE}, {MAX_TAX_RATE}]")


class TaxRateResponse(BaseModel):
    """
    Состояние налоговой политики фракции: то, что рисует ползунок и подсказка к нему.
    """

    faction_id: str = Field(...)
    rate: float = Field(...)
    band: TaxPolicyBand = Field(..., description="Режим, в который попала ставка")

    taxable_base_gold: float = Field(
        ..., description="Сбор при ставке 1.0 - цитадель плюс союзные ратуши"
    )
    forecast_income_gold: float = Field(
        ..., description="Ожидаемый сбор за такт при текущей ставке"
    )

    morale_delta: float = Field(..., description="Как ставка влияет на мораль гарнизонов")
    strike_chance: float = Field(..., description="Вероятность забастовки рабочих за такт")
    riot_chance: float = Field(..., description="Вероятность бунта в союзных землях за такт")

    @classmethod
    def from_faction(cls, faction: Faction) -> "TaxRateResponse":
        """
        Собирает ответ из агрегата фракции, чтобы роутер не считал ничего сам.
        """
        effects = faction.tax_effects
        return cls(
            faction_id=faction.id,
            rate=faction.tax_rate,
            band=effects.band,
            taxable_base_gold=faction.taxable_base_gold,
            forecast_income_gold=faction.tax_income_gold,
            morale_delta=effects.morale_delta(faction.tax_rate),
            strike_chance=effects.strike_chance,
            riot_chance=effects.riot_chance(faction.tax_rate),
        )
