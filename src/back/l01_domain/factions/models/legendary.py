"""
Шаблоны легендарных личностей: лордов, полководцев и героев.

Легендарный персонаж отличается от процедурного ровно одним: он уже
описан в каталоге геймдаты, а не сочинен мастером игры по биографии
игрока. Агрегаты у них одни и те же (Lord, Commander, Hero).

Готовые агрегаты в каталоге лежать не могут: им нужен faction_id, а он
появляется только в момент создания партии. Поэтому каталог хранит
шаблоны, а метод build(faction_id) отливает из шаблона живой агрегат.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from src.back.l01_domain.army.models.characters.commanders import (
    Commander,
    CommanderCharacteristics,
)
from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.army.models.characters.traits import Trait, get_trait
from src.back.l01_domain.common import (
    CharacterGenerationType,
    FactionRace,
    MechanicalModifier,
)
from src.back.l01_domain.factions.models.lord import Lord, LordStrategicBias


# ====================================================
# Общая часть шаблонов
# ====================================================


class LegendaryTemplate(BaseModel):
    """
    Общая часть описания легендарной личности в каталоге геймдаты.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="напр. lord_hum_benedict_strauss")
    race: FactionRace = Field(..., description="Раса, в чьем каталоге живет личность")
    name: str = Field(..., min_length=1)
    archetype: str = Field(
        default="", description="Короткое имя архетипа из docs/factions (напр. 'Технократ')"
    )
    lore_description: str = Field(default="", description="Лорное описание персонажа")

    prompt_ref: str = Field(
        ...,
        min_length=1,
        description=(
            "Логический ключ файла личности, напр. "
            "'unique_personalities.humans.lords.Benedict_Strauss'"
        ),
    )

    trait_ids: list[str] = Field(
        default_factory=list,
        description="Ключи черт из TRAITS_CATALOG (напр. ['bureaucrat', 'paranoid'])",
    )

    @property
    def faction_id(self) -> str:
        """Строковый идентификатор расового каталога (для индексов реестра)."""
        return self.race.value

    def resolve_traits(self) -> list[Trait]:
        """
        Разворачивает ключи черт в объекты каталога.
        Неизвестный ключ молча пропускается: битая строчка в геймдате не
        должна валить сборку всей партии.
        """
        traits: list[Trait] = []
        for trait_id in self.trait_ids:
            trait = get_trait(trait_id)
            if trait is not None and trait not in traits:
                traits.append(trait)
        return traits


# ====================================================
# Правители
# ====================================================


class LegendaryLordTemplate(LegendaryTemplate):
    """Описание легендарного правителя фракции в каталоге геймдаты."""

    title: str = Field(
        default="Лорд", description="Титул: Канцлер, Вождь, Эрцгерцог, Архиерей и т.д."
    )
    bias: LordStrategicBias = Field(
        default_factory=LordStrategicBias,
        description="Стратегический характер правителя в числах",
    )

    def build(self, faction_id: str) -> Lord:
        """
        Сажает легендарного правителя на трон конкретной фракции партии.
        """
        return Lord(
            faction_id=faction_id,
            name=self.name,
            title=self.title,
            generation_type=CharacterGenerationType.LEGENDARY,
            traits=self.resolve_traits(),
            is_legendary=True,
            legendary_prompt_ref=self.prompt_ref,
            lore_description=self.lore_description,
            bias=self.bias,
        )


# ====================================================
# Полководцы
# ====================================================


class LegendaryCommanderTemplate(LegendaryTemplate):
    """Описание легендарного полководца в каталоге геймдаты."""

    role_title: str = Field(
        default="Полководец", description="Воинское звание или роль в армии"
    )
    characteristics: CommanderCharacteristics = Field(
        default_factory=CommanderCharacteristics,
        description="Авторитет, тактическое чутье, живучесть и хитрость (0..100)",
    )
    fixed_equipment_ids: list[str] = Field(
        default_factory=list,
        description="Снаряжение, которое с легендарного полководца не снять",
    )

    def build(self, faction_id: str) -> Commander:
        """
        Ставит легендарного полководца под знамена конкретной фракции партии.
        """
        return Commander(
            faction_id=faction_id,
            name=self.name,
            role_title=self.role_title,
            generation_type=CharacterGenerationType.LEGENDARY,
            traits=self.resolve_traits(),
            characteristics=self.characteristics,
            is_legendary=True,
            legendary_prompt_ref=self.prompt_ref,
            fixed_equipment_ids=list(self.fixed_equipment_ids),
            lore_description=self.lore_description,
        )


# ====================================================
# Герои
# ====================================================


class LegendaryHeroTemplate(LegendaryTemplate):
    """Описание легендарной геройской карточки в каталоге геймдаты."""

    max_hp: float = Field(..., gt=0, description="Базовый запас здоровья героя")
    special_rule: str = Field(
        default="", description="Текст уникальной механики героя на поле боя"
    )
    trigger_modifier: Optional[MechanicalModifier] = Field(
        default=None, description="Пассивный механический бонус героя"
    )

    def build(self, faction_id: str) -> Hero:
        """
        Выпускает легендарного героя на карту конкретной фракции партии.
        """
        hero = Hero.create_new(
            name=self.name,
            faction_id=faction_id,
            max_hp=self.max_hp,
            special_rule=self.special_rule,
            trigger_modifier=self.trigger_modifier,
            traits=self.resolve_traits(),
            generation_type=CharacterGenerationType.LEGENDARY,
            is_legendary=True,
            legendary_prompt_ref=self.prompt_ref,
        )
        hero.lore_description = self.lore_description
        return hero
