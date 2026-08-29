"""
Настройки новой партии: что игрок выбрал в лобби до первого такта.

Это входные данные генератора мира и ничего больше: сами модели мир не
собирают и о существовании WorldState не знают. Их задача - зафиксировать
выбор игрока в валидном виде, чтобы генератор получил заведомо пригодный
набор настроек, а не разбирал полуфабрикат по крупицам.

Зерно (seed) лежит здесь же и живет вместе с партией: одна и та же связка
"настройки + зерно" всегда дает одну и ту же карту, что нужно и для
воспроизведения багов, и для модульных тестов.
"""

import random
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.back.l01_domain.common import PLAYABLE_RACES, FactionRace
from src.back.l01_domain.exceptions.world import InvalidStartingSetupError
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.world.constants import DifficultyLevel
from src.back.l01_domain.world.models.victory import VictoryConditionConfig

# Разрядность случайного зерна, если игрок не задал свое. Числа такой длины
# удобно и показывать игроку, и просить его продиктовать обратно
RANDOM_SEED_BITS: int = 32


def new_random_seed() -> int:
    """
    Свежее зерно для партии, начатой без явно указанного игроком сида.
    """
    return random.getrandbits(RANDOM_SEED_BITS)


# ==================================================================
# ПРАВИТЕЛЬ СТОРОНЫ
# ==================================================================


class RulerSetupConfig(BaseModel):
    """
    Кто сядет на трон стороны.

    Два взаимоисключающих пути: взять легендарного правителя из каталога
    геймдаты по его идентификатору либо посадить уже собранного мастером
    игры кастомного лорда. Пустая настройка - тоже законный выбор: генератор
    возьмет первого легендарного правителя расы, чтобы партия могла начаться
    вообще без похода в лобби.
    """

    legendary_lord_id: Optional[str] = Field(
        default=None,
        description="Идентификатор легендарного правителя из каталога геймдаты",
    )
    custom_lord: Optional[Lord] = Field(
        default=None,
        description="Готовый правитель, сочиненный мастером игры по биографии игрока",
    )

    @model_validator(mode="after")
    def _validate_single_source(self) -> "RulerSetupConfig":
        """
        Трон один: одновременно назвать легенду и привести своего лорда нельзя.
        """
        if self.legendary_lord_id is not None and self.custom_lord is not None:
            raise InvalidStartingSetupError(
                "у стороны указан и легендарный правитель, и кастомный лорд"
            )
        return self

    @property
    def is_empty(self) -> bool:
        """Игрок не выбирал правителя - решение остается за генератором."""
        return self.legendary_lord_id is None and self.custom_lord is None


# ==================================================================
# ОТДЕЛЬНАЯ СТОРОНА ПАРТИИ
# ==================================================================


class FactionSetupConfig(BaseModel):
    """
    Настройки одной стороны: раса, название державы и ее правитель.
    """

    race: FactionRace = Field(..., description="Раса, за которую играет сторона")
    name: str = Field(..., min_length=1, description="Название державы в этой партии")
    is_player_controlled: bool = Field(default=False)
    ruler: RulerSetupConfig = Field(default_factory=RulerSetupConfig)

    @model_validator(mode="after")
    def _validate_playable_race(self) -> "FactionSetupConfig":
        """
        Не пускает в партию расу без собственной державы: у наемников и
        нейтралов нет ни зданий, ни правителей, поэтому цитадель им ставить
        не из чего.
        """
        if self.race not in PLAYABLE_RACES:
            raise InvalidStartingSetupError(
                f"за расу '{self.race.value}' партию начать нельзя"
            )
        return self


# ==================================================================
# ПАРТИЯ ЦЕЛИКОМ
# ==================================================================


class NewGameConfig(BaseModel):
    """
    Полный набор настроек создаваемой партии.

    Базовый сценарий - "игрок против одного соперника-ИИ на противоположных
    цитаделях" плюс опциональные независимые баронства третьей силой в
    центре карты.
    """

    model_config = ConfigDict(frozen=True)

    seed: Union[int, str] = Field(
        default_factory=new_random_seed,
        description="Зерно генератора: одинаковое зерно дает одинаковую карту",
    )
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.NORMAL)

    player_faction: FactionSetupConfig = Field(..., description="Держава игрока")
    rival_faction: FactionSetupConfig = Field(..., description="Держава соперника-ИИ")

    include_baronies: bool = Field(
        default=True,
        description=(
            "Ставить ли на карту независимые баронства третьей силой. "
            "Опция вкладки «Специальные возможности» в лобби"
        ),
    )
    baronies_name: str = Field(
        default="Независимые баронства",
        min_length=1,
        description="Название державы баронств, если они участвуют в партии",
    )
    baronies_ruler: RulerSetupConfig = Field(
        default_factory=RulerSetupConfig,
        description="Правитель баронств. Учитывается только при include_baronies",
    )

    victory_config: VictoryConditionConfig = Field(
        default_factory=VictoryConditionConfig,
        description="Правила победы создаваемой партии",
    )

    @model_validator(mode="after")
    def _validate_sides(self) -> "NewGameConfig":
        """
        В партии ровно один играющий человек: смотреть на карту вторыми
        глазами некому, а без игрока не для кого считать туман войны.
        """
        if not self.player_faction.is_player_controlled:
            raise InvalidStartingSetupError("сторона игрока не помечена как игровая")
        if self.rival_faction.is_player_controlled:
            raise InvalidStartingSetupError("соперник-ИИ помечен как сторона игрока")
        return self

    @property
    def starting_sides(self) -> list[FactionSetupConfig]:
        """
        Стороны партии в порядке их появления на карте: игрок на Северной
        цитадели, соперник на Южной, баронства - в центре Ничьей земли.
        """
        sides = [self.player_faction, self.rival_faction]
        if self.include_baronies:
            sides.append(
                FactionSetupConfig(
                    race=FactionRace.BARONIAL_TROOPS,
                    name=self.baronies_name,
                    is_player_controlled=False,
                    ruler=self.baronies_ruler,
                )
            )
        return sides
