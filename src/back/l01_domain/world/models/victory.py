"""
Глобальные цели партии: правила победы, срез прогресса фракции и вердикт
о финале.

Партию можно выиграть тремя разными способами (см. VictoryType), и каждый
из них - это сравнение состояния мира с набором порогов. Пороги не зашиты
намертво: сценарий или уровень сложности подменяет их через
VictoryConditionConfig, который лежит в самом WorldState и уезжает в
сохранение вместе с партией.

Сами модели ничего не считают по миру - они только описывают цель, замер и
итог. Замер снимает VictoryEvaluator в слое сценариев: доменные модели о
существовании WorldState не знают.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.back.l01_domain.factions.constants import (
    MAX_BORDER_TOWN_LEVEL,
    MIN_BORDER_TOWN_LEVEL,
)
from src.back.l01_domain.world.constants import (
    VICTORY_ECONOMIC_FOOD,
    VICTORY_ECONOMIC_GOLD,
    VICTORY_ECONOMIC_MATERIAL,
    VICTORY_EXPANSION_TOWNS_COUNT,
    VICTORY_EXPANSION_TOWN_LEVEL,
    VictoryType,
)

# Порядок, в котором проверяются цели. Военная победа идет первой: если
# соперников не осталось, партия закончена независимо от состояния казны
VICTORY_CHECK_ORDER: tuple[VictoryType, ...] = (
    VictoryType.DOMINATION,
    VictoryType.ECONOMIC,
    VictoryType.EXPANSION,
)


def _ratio(current: float, target: float) -> float:
    """
    Доля выполнения цели от 0.0 до 1.0 для полоски прогресса в интерфейсе.

    Нулевой порог считается взятым: цель, которой нет, не может быть
    недостигнутой.
    """
    if target <= 0:
        return 1.0
    return min(1.0, max(0.0, current / target))


# ==================================================================
# ПРАВИЛА ПАРТИИ
# ==================================================================


class VictoryConditionConfig(BaseModel):
    """
    Настройки глобальных целей конкретной партии.

    Кроме самих порогов держит флаги активности: в лобби можно отключить
    любую ветку - например, оставить только войну, - и тогда выполнение ее
    условий партию не завершает.
    """

    model_config = ConfigDict(frozen=True)

    gold_threshold: float = Field(default=VICTORY_ECONOMIC_GOLD, ge=0)
    material_threshold: float = Field(default=VICTORY_ECONOMIC_MATERIAL, ge=0)
    food_threshold: float = Field(default=VICTORY_ECONOMIC_FOOD, ge=0)

    towns_count: int = Field(
        default=VICTORY_EXPANSION_TOWNS_COUNT,
        ge=1,
        description="Сколько развитых пограничных городов нужно держать разом",
    )
    town_level: int = Field(
        default=VICTORY_EXPANSION_TOWN_LEVEL,
        ge=MIN_BORDER_TOWN_LEVEL,
        le=MAX_BORDER_TOWN_LEVEL,
        description="Уровень, начиная с которого город идет в зачет",
    )

    is_domination_enabled: bool = Field(default=True)
    is_economic_enabled: bool = Field(default=True)
    is_expansion_enabled: bool = Field(default=True)

    def is_enabled(self, victory_type: VictoryType) -> bool:
        """Разыгрывается ли эта ветка победы в текущей партии."""
        flags = {
            VictoryType.DOMINATION: self.is_domination_enabled,
            VictoryType.ECONOMIC: self.is_economic_enabled,
            VictoryType.EXPANSION: self.is_expansion_enabled,
        }
        return flags[victory_type]

    @property
    def enabled_types(self) -> tuple[VictoryType, ...]:
        """
        Активные цели в порядке проверки. Пустой кортеж - партия без победы:
        закончить ее можно только поражением.
        """
        return tuple(vt for vt in VICTORY_CHECK_ORDER if self.is_enabled(vt))


# ==================================================================
# ЗАМЕР ПРОГРЕССА
# ==================================================================


class VictoryProgress(BaseModel):
    """
    Срез продвижения одной фракции ко всем трем целям на конкретном такте.

    Замер несет и текущие значения, и пороги, по которым он снят: полоска
    прогресса в интерфейсе и подсказка советника считаются прямо отсюда, не
    заглядывая в настройки партии.
    """

    model_config = ConfigDict(frozen=True)

    faction_id: str = Field(..., min_length=1)

    # ----- Территориальное господство -----
    domination_defeated_factions: int = Field(
        default=0, ge=0, description="Сколько соперников уже выбыло из партии"
    )
    domination_total_enemies: int = Field(
        default=0, ge=0, description="Сколько всего соперников было на карте"
    )

    # ----- Экономическое процветание -----
    current_gold: float = Field(default=0.0, ge=0)
    current_material: float = Field(default=0.0, ge=0)
    current_food: float = Field(default=0.0, ge=0)

    target_gold: float = Field(default=VICTORY_ECONOMIC_GOLD, ge=0)
    target_material: float = Field(default=VICTORY_ECONOMIC_MATERIAL, ge=0)
    target_food: float = Field(default=VICTORY_ECONOMIC_FOOD, ge=0)

    # ----- Основание страны -----
    max_level_towns_count: int = Field(
        default=0, ge=0, description="Города, дотянувшие до требуемого уровня"
    )
    required_towns_count: int = Field(default=VICTORY_EXPANSION_TOWNS_COUNT, ge=1)
    required_town_level: int = Field(
        default=VICTORY_EXPANSION_TOWN_LEVEL,
        ge=MIN_BORDER_TOWN_LEVEL,
        le=MAX_BORDER_TOWN_LEVEL,
    )

    @model_validator(mode="after")
    def _validate_domination_counters(self) -> "VictoryProgress":
        """
        Побежденных соперников не может быть больше, чем их было на карте:
        такой замер означал бы ошибку подсчета, а не близкую победу.
        """
        if self.domination_defeated_factions > self.domination_total_enemies:
            raise ValueError(
                "Побежденных соперников больше, чем их всего: "
                f"{self.domination_defeated_factions} из {self.domination_total_enemies}"
            )
        return self

    # ==================================================================
    # ДОСТИГНУТА ЛИ ЦЕЛЬ
    # ==================================================================

    @property
    def is_domination_complete(self) -> bool:
        """
        Соперников не осталось.

        Партия в одиночестве победой не считается: побеждать некого, и
        условие остается невыполненным до появления на карте противника.
        """
        return (
            self.domination_total_enemies > 0
            and self.domination_defeated_factions >= self.domination_total_enemies
        )

    @property
    def is_economic_complete(self) -> bool:
        """
        Казна держит все три порога разом. Нехватка одной единицы любого
        ресурса блокирует победу целиком.
        """
        return (
            self.current_gold >= self.target_gold
            and self.current_material >= self.target_material
            and self.current_food >= self.target_food
        )

    @property
    def is_expansion_complete(self) -> bool:
        """
        Нужное число городов стоит на нужном уровне прямо сейчас.

        Замер моментальный: разграбленный город, просевший до второго
        уровня, тут же выпадает из зачета и обнуляет достижение цели.
        """
        return self.max_level_towns_count >= self.required_towns_count

    def is_complete(self, victory_type: VictoryType) -> bool:
        """Выполнено ли условие конкретной ветки победы."""
        checks = {
            VictoryType.DOMINATION: self.is_domination_complete,
            VictoryType.ECONOMIC: self.is_economic_complete,
            VictoryType.EXPANSION: self.is_expansion_complete,
        }
        return checks[victory_type]

    # ==================================================================
    # ПОЛОСКИ ПРОГРЕССА ДЛЯ ИНТЕРФЕЙСА
    # ==================================================================

    @property
    def domination_ratio(self) -> float:
        return _ratio(self.domination_defeated_factions, self.domination_total_enemies)

    @property
    def economic_ratio(self) -> float:
        """
        Прогресс по самому отстающему ресурсу: экономическая победа идет со
        скоростью пустейшего из трех складов.
        """
        return min(
            _ratio(self.current_gold, self.target_gold),
            _ratio(self.current_material, self.target_material),
            _ratio(self.current_food, self.target_food),
        )

    @property
    def expansion_ratio(self) -> float:
        return _ratio(self.max_level_towns_count, self.required_towns_count)

    def ratio(self, victory_type: VictoryType) -> float:
        """Доля выполнения конкретной ветки победы."""
        ratios = {
            VictoryType.DOMINATION: self.domination_ratio,
            VictoryType.ECONOMIC: self.economic_ratio,
            VictoryType.EXPANSION: self.expansion_ratio,
        }
        return ratios[victory_type]


# ==================================================================
# ВЕРДИКТ О ФИНАЛЕ
# ==================================================================


class VictoryEvaluationResult(BaseModel):
    """
    Итог проверки мира на условия победы и поражения.

    Прогресс кладется по всем сторонам сразу: тот же вердикт уходит и на
    экран финала, и в контекст летописца, которому нужно знать, чем именно
    закончилась партия у каждого.
    """

    model_config = ConfigDict(frozen=True)

    is_game_over: bool = Field(default=False)
    is_player_victorious: bool = Field(default=False)

    victory_type: Optional[VictoryType] = Field(
        default=None, description="Ветка, по которой партия закончилась. None при поражении"
    )
    winner_faction_id: Optional[str] = Field(
        default=None, description="Кто выиграл. None, если партия оборвалась поражением игрока"
    )

    reason: str = Field(
        default="", description="Стилизованная причина финала для экрана и летописца"
    )
    progress: dict[str, VictoryProgress] = Field(
        default_factory=dict, description="Срез прогресса всех сторон: faction_id -> замер"
    )

    def get_progress(self, faction_id: str) -> Optional[VictoryProgress]:
        """Замер конкретной стороны на момент вердикта."""
        return self.progress.get(faction_id)
