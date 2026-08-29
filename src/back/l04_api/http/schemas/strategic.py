"""
Схемы приказов глобальной карты: марш армий, рабочие, экспедиции,
налоги, пограничные города и гарнизоны земель.
"""

from typing import Optional

from pydantic import BaseModel, Field

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.factions.constants import (
    BorderTownResolutionType,
    GARRISON_FOOD_UPKEEP_DISCOUNT_RATIO,
    MAX_BORDER_TOWN_ALLIED_LANDS,
    MAX_BORDER_TOWN_LEVEL,
    MAX_STATIONED_GARRISON_SQUADS,
    MAX_TAX_RATE,
    MIN_TAX_RATE,
    ResourceType,
    TaxPolicyBand,
)
from src.back.l01_domain.factions.models.border_town import (
    BorderTown,
    BorderTownOperation,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.garrison import Garrison
from src.back.l01_domain.maps.constants import HexVisibilityState
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.constants import VictoryType
from src.back.l01_domain.world.models.victory import (
    VictoryConditionConfig,
    VictoryProgress,
)
from src.back.l01_domain.world.models.visibility import FactionVisionMap


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
# Судьба побежденного пограничного города
# ====================================================


class ResolveBorderTownRequest(BaseModel):
    """
    Решение победителя о судьбе взятого города. Сам город задан town_id в пути.
    """

    army_id: str = Field(
        ..., min_length=1, description="Армия победителя, стоящая на гексе города"
    )
    resolution_type: BorderTownResolutionType = Field(
        ..., description="Сжечь, разграбить, занять или пройти мимо"
    )


class BorderTownOperationResponse(BaseModel):
    """
    Состояние операции над городом: то, что рисует окно взятого поселения.

    Пустой operation_id означает, что города никто не разоряет: победитель
    прошел мимо либо ничего еще не решил.
    """

    operation_id: Optional[str] = Field(
        default=None, description="Идентификатор идущей операции, если она есть"
    )
    town_id: str = Field(...)
    resolution_type: BorderTownResolutionType = Field(...)
    ticks_remaining: int = Field(
        ..., ge=0, description="Сколько тактов осталось до наступления последствий"
    )
    estimated_loot: dict[ResourceType, float] = Field(
        default_factory=dict,
        description="Что уйдет в казну победителя, когда операция завершится",
    )

    @classmethod
    def from_operation(
        cls, operation: BorderTownOperation
    ) -> "BorderTownOperationResponse":
        """Ответ по идущей операции - вместе с ее обратным отсчетом."""
        return cls(
            operation_id=operation.id,
            town_id=operation.town_id,
            resolution_type=operation.resolution_type,
            ticks_remaining=operation.ticks_remaining,
            estimated_loot=operation.loot,
        )

    @classmethod
    def idle(cls, town_id: str) -> "BorderTownOperationResponse":
        """
        Ответ по городу, над которым ничего не происходит.

        Это ровно тот же исход, что и осознанный пропуск, поэтому и тип
        резолюции у него тот же - IGNORE.
        """
        return cls(
            town_id=town_id,
            resolution_type=BorderTownResolutionType.IGNORE,
            ticks_remaining=0,
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


# ====================================================
# Глобальные цели партии
# ====================================================


class VictoryBranchView(BaseModel):
    """
    Одна ветка глобальной цели в панели интерфейса: подпись, полоска
    прогресса и признак взятой планки.
    """

    victory_type: VictoryType = Field(...)
    is_enabled: bool = Field(..., description="Разыгрывается ли эта ветка в партии")
    is_complete: bool = Field(..., description="Условие выполнено прямо сейчас")
    ratio: float = Field(..., ge=0.0, le=1.0, description="Доля выполнения от 0 до 1")
    current: str = Field(..., description="Текущие значения строкой для подсказки")
    target: str = Field(..., description="Требуемые значения строкой для подсказки")


class VictoryProgressResponse(BaseModel):
    """
    Сводка продвижения фракции к глобальным целям.

    Собирается из доменного замера: роутер сам ничего не считает, а панель
    целей получает готовые проценты и подписи.
    """

    faction_id: str = Field(...)
    is_finished: bool = Field(..., description="Партия уже дошла до финала")
    branches: list[VictoryBranchView] = Field(default_factory=list)

    @classmethod
    def from_progress(
        cls,
        progress: VictoryProgress,
        config: VictoryConditionConfig,
        is_finished: bool = False,
    ) -> "VictoryProgressResponse":
        """
        Раскладывает замер по трем веткам панели.
        """
        labels = {
            VictoryType.DOMINATION: (
                f"{progress.domination_defeated_factions} соперников выбито",
                f"{progress.domination_total_enemies} соперников на карте",
            ),
            VictoryType.ECONOMIC: (
                f"{progress.current_gold:.0f} золота, "
                f"{progress.current_material:.0f} материалов, "
                f"{progress.current_food:.0f} провизии",
                f"{progress.target_gold:.0f} золота, "
                f"{progress.target_material:.0f} материалов, "
                f"{progress.target_food:.0f} провизии",
            ),
            VictoryType.EXPANSION: (
                f"{progress.max_level_towns_count} городов "
                f"{progress.required_town_level}-го уровня",
                f"{progress.required_towns_count} городов "
                f"{progress.required_town_level}-го уровня",
            ),
        }

        return cls(
            faction_id=progress.faction_id,
            is_finished=is_finished,
            branches=[
                VictoryBranchView(
                    victory_type=victory_type,
                    is_enabled=config.is_enabled(victory_type),
                    is_complete=progress.is_complete(victory_type),
                    ratio=progress.ratio(victory_type),
                    current=current,
                    target=target,
                )
                for victory_type, (current, target) in labels.items()
            ],
        )


class VictoryOverviewResponse(BaseModel):
    """
    Панель глобальных целей целиком: сводка игрока и сводки его соперников.

    Соперники показываются теми же полосками: скрытых зон в этих числах
    нет - казна и уровни чужих городов видны разведке и так.
    """

    player: Optional[VictoryProgressResponse] = Field(
        default=None, description="Сводка фракции игрока. None у партии-наблюдения"
    )
    rivals: list[VictoryProgressResponse] = Field(default_factory=list)


# ====================================================
# Туман войны
# ====================================================


class FactionVisionResponse(BaseModel):
    """
    Маска тумана войны для слоя карты в интерфейсе.

    Множества гексов приходят списками: JSON множеств не знает, а порядок
    отрисовке слоя безразличен. Гексы прямого обзора в explored_hexes не
    дублируются - клиент рисует их поверх разведанных.
    """

    faction_id: str = Field(...)
    visible_hexes: list[HexCoordinates] = Field(
        default_factory=list, description="Гексы под прямым обзором на текущий такт"
    )
    explored_hexes: list[HexCoordinates] = Field(
        default_factory=list,
        description="Гексы, открытые ранее: ландшафт известен, движение скрыто",
    )
    visible_count: int = Field(default=0, ge=0)
    explored_count: int = Field(default=0, ge=0)

    @classmethod
    def from_vision_map(cls, vision_map: FactionVisionMap) -> "FactionVisionResponse":
        """
        Раскладывает доменную маску в упорядоченные списки для клиента.
        """
        ordered = sorted(vision_map.visible_hexes, key=lambda c: (c.q, c.r))
        fogged = sorted(
            vision_map.explored_hexes - vision_map.visible_hexes,
            key=lambda c: (c.q, c.r),
        )

        return cls(
            faction_id=vision_map.faction_id,
            visible_hexes=ordered,
            explored_hexes=fogged,
            visible_count=len(vision_map.visible_hexes),
            explored_count=len(vision_map.explored_hexes),
        )


class HexVisibilityResponse(BaseModel):
    """
    Состояние одного гекса глазами фракции - для подсказки под курсором.
    """

    faction_id: str = Field(...)
    hex_coordinates: HexCoordinates = Field(...)
    state: HexVisibilityState = Field(...)
