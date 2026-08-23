"""
Схемы генерации и DTO для общения с LLM Оружейника.
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.army.constants import EquipmentSlot, EquipmentTag


class StatPriorities(BaseModel):
    """
    Относительные приоритеты характеристик (от 0 до 10), определяемые LLM.
    Нейросеть не придумывает точный урон, она расставляет акценты на основе
    запроса игрока.
    """

    damage: int = Field(default=0, ge=0, le=10, description="Приоритет базового урона")
    armor_piercing: int = Field(default=0, ge=0, le=10, description="Приоритет пробития брони")
    armor_bonus: int = Field(default=0, ge=0, le=10, description="Приоритет защиты")
    range_hexes: int = Field(default=0, ge=0, le=10, description="Приоритет дальности атаки")

    # Трейд-оффы (штрафы). Увеличение штрафа дает больше бюджета на основные характеристики.
    heavy_weight_tradeoff: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Готовность пожертвовать скоростью перемещения ради огневой мощи или толщины брони",
    )
    clunkiness_tradeoff: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Готовность пожертвовать инициативой (скоростью реакции в бою)",
    )


class LLMGunsmithResponse(BaseModel):
    """
    Ожидаемая JSON-схема ответа от LLM Оружейника.
    Именно в этот формат LLMExecutor будет парсить ответ нейросети.
    """

    is_approved: bool = Field(
        ...,
        description="Одобрил ли мастер создание такого предмета (соответствует ли лору и технологиям фракции)",
    )
    master_reply: str = Field(
        ...,
        description="Художественный ответ мастера игроку (отказ или комментарий к чертежу)",
    )

    # Следующие поля заполняются только если is_approved == True
    name: Optional[str] = Field(default=None, description="Название предмета")
    lore: Optional[str] = Field(
        default=None, description="Краткое описание предмета для интерфейса"
    )
    tier: Optional[int] = Field(
        default=None, ge=1, le=6, description="Присвоенный тир предмета (от 1 до 6)"
    )

    slot: Optional[EquipmentSlot] = Field(
        default=None, description="Слот экипировки (weapon, armor, accessory)"
    )
    category_name: Optional[str] = Field(
        default=None,
        description="Название категории (напр. 'sword', 'plate', 'shield', 'firearm')",
    )
    tags: list[EquipmentTag] = Field(
        default_factory=list,
        description="Набор механических и лорных тегов (two_handed, heavy, blackpowder и т.д.)",
    )

    priorities: Optional[StatPriorities] = Field(
        default=None, description="Матрица приоритетов для расчета баланса"
    )
    special_rules: Optional[str] = Field(
        default=None,
        description="Текстовое описание уникальной механики, если игрок просил нечто нестандартное",
    )
