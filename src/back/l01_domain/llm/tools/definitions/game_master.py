"""
Определения инструментов мастера игры.
"""

from src.back.l01_domain.llm.models.tools import ToolDefinition
from src.back.l01_domain.llm.tools.schemas.game_master import (
    CreateAdvisorParams,
    CreateCommanderParams,
    CreateHeroParams,
    CreateLordParams,
    RejectCreationParams,
    TriggerWorldEventParams,
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
