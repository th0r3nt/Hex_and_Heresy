"""
Схемы приказов глобальной карты: марш армий, рабочие, экспедиции,
налоги, пограничные города и гарнизоны земель.
"""

from pydantic import BaseModel, Field

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.factions.constants import (
    GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO,
    MAX_BORDER_TOWN_ALLIED_LANDS,
    MAX_BORDER_TOWN_LEVEL,
    MAX_STATIONED_GARRISON_SQUADS,
    MAX_TAX_RATE,
    MIN_TAX_RATE,
    ResourceType,
    TaxPolicyBand,
)
from src.back.l01_domain.factions.models.border_town import BorderTown
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.garrison import Garrison
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
        ...,
        description="Сбор при ставке 1.0 - цитадель, пограничные города и союзные ратуши",
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


# ====================================================
# Пограничные города
# ====================================================


class FoundBorderTownRequest(BaseModel):
    """
    Приказ основать пограничный город на свободном гексе карты.
    """

    faction_id: str = Field(..., min_length=1, description="Кто основывает поселение")
    target_hex: HexCoordinates = Field(..., description="Свободный гекс под город")
    name: str = Field(..., min_length=1, description="Как основатель называет город")


class UpgradeBorderTownRequest(BaseModel):
    """
    Приказ поднять город на уровень выше. Сам город задан town_id в пути.
    """

    faction_id: str = Field(..., min_length=1, description="Владелец города")


class ClaimBorderLandRequest(BaseModel):
    """
    Приказ выкупить городу смежную землю. Город задан town_id в пути.
    """

    faction_id: str = Field(..., min_length=1, description="Владелец города")
    target_hex: HexCoordinates = Field(
        ..., description="Гекс, вплотную примыкающий к городу"
    )


class BorderTownResponse(BaseModel):
    """
    Состояние пограничного города: то, что рисует окно поселения.
    """

    id: str = Field(...)
    faction_id: str = Field(...)
    name: str = Field(...)

    level: int = Field(..., description=f"Уровень города, потолок - {MAX_BORDER_TOWN_LEVEL}")
    center_hex: HexCoordinates = Field(..., description="Гекс, на котором стоит город")
    zone_id: str = Field(..., description="Ключ земли города в формате 'q,r'")

    claimed_hexes: list[HexCoordinates] = Field(
        default_factory=list, description="Выкупленные городом союзные земли"
    )
    free_land_slots: int = Field(
        ...,
        description=f"Сколько земель город еще заселит (лимит {MAX_BORDER_TOWN_ALLIED_LANDS})",
    )

    building_slots: int = Field(..., description="Строительные слоты внутри самого города")
    invested_resources: dict[ResourceType, float] = Field(
        default_factory=dict,
        description="Во что городу обошлись основание, апгрейды и выкуп земель",
    )

    @classmethod
    def from_border_town(cls, town: BorderTown) -> "BorderTownResponse":
        """
        Собирает ответ из агрегата, чтобы роутер ничего не считал сам.
        """
        return cls(
            id=town.id,
            faction_id=town.faction_id,
            name=town.name,
            level=town.level,
            center_hex=town.center_hex,
            zone_id=town.zone_id,
            claimed_hexes=list(town.claimed_hexes),
            free_land_slots=town.free_land_slots,
            building_slots=town.building_slots,
            invested_resources=dict(town.invested_resources),
        )


# ====================================================
# Гарнизоны земель
# ====================================================


class StationSquadRequest(BaseModel):
    """
    Приказ оставить отряд армии за стенами земли.
    Земля задается zone_id в пути запроса.
    """

    army_id: str = Field(..., min_length=1, description="Армия, стоящая на гексе гарнизона")
    squad_id: str = Field(..., min_length=1, description="Отряд, который остается в гарнизоне")


class UnstationSquadRequest(BaseModel):
    """
    Приказ забрать расквартированный отряд обратно в мобильную армию.
    """

    army_id: str = Field(..., min_length=1, description="Армия, которая примет отряд")
    squad_id: str = Field(..., min_length=1, description="Расквартированный отряд")


class GarrisonSquadView(BaseModel):
    """
    Строка списка защитников для окна управления землей.
    """

    id: str = Field(...)
    name: str = Field(..., description="Имя отряда или его ветеранское прозвище")
    tier: int = Field(...)
    unit_count: int = Field(..., description="Сколько бойцов в строю прямо сейчас")
    full_unit_count: int = Field(..., description="Полный штат отряда")
    morale: float = Field(...)

    @classmethod
    def from_squad(cls, squad: Squad) -> "GarrisonSquadView":
        return cls(
            id=squad.id,
            name=squad.display_name,
            tier=squad.archetype.tier,
            unit_count=squad.state.unit_count,
            full_unit_count=squad.archetype.default_unit_count,
            morale=squad.state.morale,
        )


class GarrisonResponse(BaseModel):
    """
    Состояние гарнизона земли: то, что рисует окно обороны зоны.
    """

    zone_id: str = Field(...)
    faction_id: str = Field(...)
    hex_coordinates: HexCoordinates = Field(...)

    militia_squads: list[GarrisonSquadView] = Field(
        default_factory=list, description="Городское ополчение, поднятое самой землей"
    )
    stationed_squads: list[GarrisonSquadView] = Field(
        default_factory=list, description="Регулярные войска, оставленные игроком"
    )

    free_stationed_slots: int = Field(
        ..., description=f"Сколько карточек земля еще примет (лимит {MAX_STATIONED_GARRISON_SQUADS})"
    )
    total_units_count: int = Field(..., description="Сколько живых бойцов держит землю")

    upkeep_gold: float = Field(..., description="Жалование гарнизона за такт")
    upkeep_food: float = Field(
        ...,
        description=(
            "Расход провизии за такт уже со скидкой "
            f"{int(GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO * 100)}% за жизнь на городских запасах"
        ),
    )

    is_locked_in_battle: bool = Field(
        ..., description="За землю идет бой: состав гарнизона заморожен"
    )

    @classmethod
    def from_garrison(cls, garrison: Garrison) -> "GarrisonResponse":
        """
        Собирает ответ из агрегата, чтобы роутер ничего не считал сам.
        """
        return cls(
            zone_id=garrison.zone_id,
            faction_id=garrison.faction_id,
            hex_coordinates=garrison.hex_coordinates,
            militia_squads=[
                GarrisonSquadView.from_squad(s) for s in garrison.militia_squads
            ],
            stationed_squads=[
                GarrisonSquadView.from_squad(s) for s in garrison.stationed_squads
            ],
            free_stationed_slots=garrison.free_stationed_slots,
            total_units_count=garrison.total_units_count,
            upkeep_gold=garrison.total_upkeep_gold,
            upkeep_food=garrison.total_upkeep_food,
            is_locked_in_battle=garrison.is_locked_in_battle,
        )
