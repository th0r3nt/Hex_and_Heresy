"""
Инструменты оружейной мастерской (создание и валидация чертежей экипировки).
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.army.constants import EquipmentSlot, EquipmentTag
from src.back.l01_domain.llm.models.skills import ToolDefinition


class DraftBlueprintParams(BaseModel):
    """Параметры создания чертежа кастомного снаряжения."""

    name: str = Field(..., min_length=1, description="Название создаваемого предмета")
    lore: str = Field(
        default="Создано в мастерской по особому заказу.",
        description="Краткое описание предмета для интерфейса",
    )
    slot: EquipmentSlot = Field(
        ..., description="Слот экипировки: weapon, armor или accessory"
    )
    category_name: Optional[str] = Field(
        default=None, description="Подтип предмета (напр. 'sword', 'plate', 'shield')"
    )
    tier: int = Field(default=1, ge=1, le=6, description="Присвоенный тир предмета от 1 до 6")
    tags: list[EquipmentTag] = Field(
        default_factory=list, description="Теги снаряжения (two_handed, heavy, blackpowder и т.д.)"
    )
    damage_priority: int = Field(default=0, ge=0, le=10, description="Приоритет урона")
    armor_piercing_priority: int = Field(
        default=0, ge=0, le=10, description="Приоритет пробития брони"
    )
    armor_bonus_priority: int = Field(default=0, ge=0, le=10, description="Приоритет защиты")
    range_priority: int = Field(default=0, ge=0, le=10, description="Приоритет дальности атаки")
    heavy_weight_tradeoff: int = Field(
        default=0, ge=0, le=10, description="Штраф к скорости за дополнительный бюджет характеристик"
    )
    clunkiness_tradeoff: int = Field(
        default=0, ge=0, le=10, description="Штраф к инициативе за дополнительный бюджет характеристик"
    )
    master_reply: str = Field(
        ..., description="Художественный комментарий мастера-оружейника к созданному чертежу"
    )
    special_rules: Optional[str] = Field(
        default=None, description="Текстовое описание уникальной способности предмета"
    )


class RejectBlueprintParams(BaseModel):
    """Параметры мотивированного отказа мастера в изготовлении предмета."""

    reason: str = Field(..., min_length=1, description="Техническая или лорная причина отказа")
    master_reply: str = Field(
        ..., min_length=1, description="Стилизованная реплика мастера с отказом правителю"
    )


DRAFT_BLUEPRINT = ToolDefinition(
    name="draft_blueprint",
    description="Спроектировать чертеж нового предмета экипировки с расчетом характеристик и стоимости.",
    parameters_model=DraftBlueprintParams,
)

REJECT_BLUEPRINT = ToolDefinition(
    name="reject_blueprint",
    description="Отклонить запрос на создание предмета, если идея противоречит лору или культуре расы.",
    parameters_model=RejectBlueprintParams,
)