"""
Инструменты мастера игры (создание кастомных персонажей и динамических событий).
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.common import MechanicalModifier
from src.back.l01_domain.llm.models.skills import ToolDefinition
from src.back.l01_domain.world.constants import GlobalEventCategory, GlobalEventScope


class CreateCommanderParams(BaseModel):
    """Параметры создания кастомного полководца."""

    name: str = Field(..., min_length=1, description="Имя полководца")
    role_title: str = Field(..., min_length=1, description="Воинское звание или роль")
    distilled_personality: str = Field(
        ..., min_length=1, description="Сжатое описание характера и манеры речи"
    )
    trait_ids: list[str] = Field(
        default_factory=list, description="Идентификаторы черт характера из каталога"
    )
    authority: int = Field(default=10, ge=0, le=100, description="Авторитет")
    tactical_acumen: int = Field(default=10, ge=0, le=100, description="Тактическое чутье")
    resilience: int = Field(default=10, ge=0, le=100, description="Живучесть")
    cunning: int = Field(default=10, ge=0, le=100, description="Хитрость")
    master_reply: str = Field(..., description="Комментарий мастера игры")


class CreateHeroParams(BaseModel):
    """Параметры создания кастомного героя."""

    name: str = Field(..., min_length=1, description="Имя героя")
    special_rule: str = Field(
        ..., min_length=1, description="Уникальная тактическая способность героя"
    )
    max_hp: float = Field(
        default=120.0, ge=50.0, le=400.0, description="Базовый запас здоровья"
    )
    distilled_personality: str = Field(..., description="Характер и стиль поведения")
    trait_ids: list[str] = Field(default_factory=list, description="Черты характера")
    master_reply: str = Field(..., description="Комментарий мастера игры")


class CreateLordParams(BaseModel):
    """Параметры создания правителя фракции."""

    name: str = Field(..., min_length=1, description="Имя правителя")
    title: str = Field(default="Лорд", description="Титул правителя")
    archetype_name: str = Field(..., description="Стиль руководства")
    distilled_personality: str = Field(..., description="Манера общения на аудиенциях")
    trait_ids: list[str] = Field(default_factory=list, description="Черты характера")
    tax_rate_bias: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Склонность к повышению налогов"
    )
    military_building_priority: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Приоритет военной застройки"
    )
    diplomatic_aggression: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Агрессивность во внешней политике"
    )
    bribery_susceptibility: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Сговорчивость при подкупе золотом"
    )
    master_reply: str = Field(..., description="Комментарий мастера игры")


class CreateAdvisorParams(BaseModel):
    """Параметры создания кастомного советника."""

    name: str = Field(..., min_length=1, description="Имя советника")
    title: str = Field(default="Первый советник", description="Должность или статус")
    distilled_personality: str = Field(..., description="Тон речи и приоритеты")
    trait_ids: list[str] = Field(default_factory=list, description="Черты характера")
    master_reply: str = Field(..., description="Комментарий мастера игры")


class TriggerWorldEventParams(BaseModel):
    """Параметры генерации динамического кризиса или аномалии."""

    name: str = Field(..., min_length=1, description="Название события")
    description: str = Field(..., min_length=1, description="Художественное описание события")
    category: GlobalEventCategory = Field(..., description="Категория события")
    scope: GlobalEventScope = Field(
        default=GlobalEventScope.GLOBAL, description="Масштаб распространения"
    )
    duration_ticks: int = Field(
        default=4, ge=1, le=20, description="Длительность действия в тактах"
    )
    target_faction_ids: list[str] = Field(default_factory=list)
    target_hex_q: Optional[int] = None
    target_hex_r: Optional[int] = None
    spawn_hostile_army: bool = False
    neutral_army_name: str = "Шайка разбойников"
    neutral_unit_type: str = "marauders"
    modifiers: list[MechanicalModifier] = Field(default_factory=list)


class RejectCreationParams(BaseModel):
    """Параметры отказа в создании персонажа при нарушении лора."""

    reason: str = Field(..., min_length=1, description="Причина отклонения концепта")
    master_reply: str = Field(
        ..., min_length=1, description="Стилизованный ответ от имени мира"
    )


CREATE_COMMANDER = ToolDefinition(
    name="create_commander",
    description="Создать кастомного полководца для найма в армию на основе биографии игрока.",
    parameters_model=CreateCommanderParams,
)

CREATE_HERO = ToolDefinition(
    name="create_hero",
    description="Создать кастомную героическую карточку для армии на основе биографии игрока.",
    parameters_model=CreateHeroParams,
)

CREATE_LORD = ToolDefinition(
    name="create_lord",
    description="Создать нового правителя фракции с индивидуальными стратегическими уклонами.",
    parameters_model=CreateLordParams,
)

CREATE_ADVISOR = ToolDefinition(
    name="create_advisor",
    description="Создать профиль персонализированного советника для интерфейса и рекомендаций.",
    parameters_model=CreateAdvisorParams,
)

TRIGGER_WORLD_EVENT = ToolDefinition(
    name="trigger_world_event",
    description="Запустить динамическое региональное или глобальное событие на карте мира.",
    parameters_model=TriggerWorldEventParams,
)

REJECT_CREATION = ToolDefinition(
    name="reject_creation",
    description="Отклонить запрос игрока на создание сущности при нарушении законов сеттинга.",
    parameters_model=RejectCreationParams,
)
