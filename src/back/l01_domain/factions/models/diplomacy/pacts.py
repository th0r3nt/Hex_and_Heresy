"""
Соглашения между двумя фракциями - экономические, военные, гарантийные.
Каждый пакт - самостоятельный value-объект; то, какие пакты сейчас
действуют между парой фракций, хранит агрегат DiplomaticRelation (relation.py).
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.factions.constants import ResourceType


class TradeAgreement(BaseModel):
    """Условия пассивного обмена ресурсами между двумя фракциями."""

    give_resource: ResourceType = Field(...)
    give_amount: float = Field(..., ge=0)
    get_resource: ResourceType = Field(...)
    get_amount: float = Field(..., ge=0)

    duration_turns: int = Field(..., ge=1)
    remaining_turns: int = Field(...)


class NonAggressionPact(BaseModel):
    """
    Договор о ненападении - юниты не могут заходить на чужие гексы без объявления войны.
    """

    allowed_hex_ids: list[str] = Field(default_factory=list)


class RightOfPassagePact(BaseModel):
    """
    Право прохода. Одна сторона (beneficiary) может свободно перемещать
    армии через указанные гексы территории другой стороны, не вступая
    в союз и не объявляя войны - как правило, за плату.
    (см. diplomacy.md, пример: "Выторгуй у эльфов право прохода за 500 золота")

    В отличие от NonAggressionPact - соглашение асимметрично: право
    получает только beneficiary_faction_id, вторая сторона не обязана
    получать проход в ответ.
    """

    beneficiary_faction_id: str = Field(..., description="Чьи армии получают право прохода")
    allowed_hex_ids: list[str] = Field(default_factory=list)
    toll_gold_per_crossing: float = Field(
        default=0.0,
        ge=0,
        description="Плата за каждое пересечение гекса (0 - бесплатный проход)",
    )
    duration_turns: int = Field(..., ge=1)
    remaining_turns: int = Field(...)


class VassalPact(BaseModel):
    """
    Вассалитет/протекторат. Вассал платит сюзерену дань каждый такт
    в обмен на обязательство военной защиты от третьих фракций.
    Асимметричное соглашение - стороны формально не равны, в отличие
    от TradeAgreement или NonAggressionPact.
    """

    overlord_faction_id: str = Field(...)
    vassal_faction_id: str = Field(...)
    tribute_gold_per_turn: float = Field(..., ge=0)
    overlord_protection_obligated: bool = Field(
        default=True,
        description="Обязан ли сюзерен вступать в войну на стороне вассала при нападении третьей фракции",
    )


class IntelligenceSharingPact(BaseModel):
    """
    Обмен разведданными. Стороны делятся информацией о перемещениях
    армий указанных третьих фракций в согласованном радиусе от своих
    гексов. (см. baronial_troops/buildings.md, "Сторожевые вышки" -
    механика продажи вскрытия тумана войны; здесь - бесплатный обмен по договору)
    """

    shared_target_faction_ids: list[str] = Field(
        default_factory=list,
        description="О перемещениях каких фракций стороны обмениваются данными",
    )
    vision_sharing_radius_hexes: int = Field(default=2, ge=1)


class HostageExchangePact(BaseModel):
    """
    Обмен заложниками как гарантия мира. Если одна из сторон разрывает
    договор и объявляет войну, её заложник считается казнённым -
    сама казнь и её последствия (удар по морали, ответная казнь) это
    забота l02_services, подписанного на событие declare_war.
    """

    faction_a_hostage_id: Optional[str] = Field(
        default=None, description="ID командира/героя фракции A, удерживаемого фракцией B"
    )
    faction_b_hostage_id: Optional[str] = Field(
        default=None, description="ID командира/героя фракции B, удерживаемого фракцией A"
    )
    executed_on_treaty_break: bool = Field(default=True)


class WarAlliancePact(BaseModel):
    """
    Военный союз против общего врага. В отличие от NonAggressionPact
    (обязательство не нападать друг на друга), обязывает стороны
    совместно воевать против конкретной третьей фракции и делить трофеи.
    """

    common_enemy_faction_id: str = Field(...)
    loot_split_ratio_a: float = Field(
        ...,
        ge=0,
        le=1,
        description="Доля трофеев фракции A от совместных побед (остаток уходит фракции B)",
    )
    duration_turns: int = Field(..., ge=1)
    remaining_turns: int = Field(...)
