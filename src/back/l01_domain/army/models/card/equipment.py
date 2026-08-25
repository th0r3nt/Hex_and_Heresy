"""
Модели предметов экипировки: оружие, броня, аксессуары.
"""

from typing import Optional, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator

from src.back.l01_domain.army.constants import (
    AccessoryCategory,
    ArmorCategory,
    EquipmentSlot,
    EquipmentTag,
    UnitSizeCategory,
    WeaponCategory,
)
from src.back.l01_domain.exceptions.army import InvalidEquipmentSlotError

EquipmentCategoryType = Union[WeaponCategory, ArmorCategory, AccessoryCategory]


class EquipmentStats(BaseModel):
    """
    Модификаторы характеристик, даваемые экипировкой.
    """

    model_config = ConfigDict(frozen=True)

    # Дополнительный урон
    damage: float = Field(default=0.0, ge=0, description="Базовый урон")
    # Дополнительная защита
    armor_piercing: float = Field(
        default=0.0, ge=0, description="Игнорирование брони цели (в ед.)"
    )
    armor_bonus: float = Field(default=0.0, ge=0, description="Бонус к броне")
    # Дополнительная дальность
    range_hexes: int = Field(default=1, ge=1, description="Дальность атаки в гексах/квадратах")
    # Модификатор скорости
    speed_modifier: float = Field(
        default=0.0, description="Модификатор скорости (-0.2 = -20%)"
    )
    # Модификатор инициативы
    initiative_modifier: int = Field(default=0, description="Модификатор очередности хода")
    # Дополнительный расход выносливости на ход
    stamina_drain_per_turn: float = Field(
        default=0.0, ge=0, description="Доп. расход выносливости за ход"
    )
    # Доп. урон против больших целей
    damage_bonus_vs_size: dict[UnitSizeCategory, float] = Field(
        default_factory=dict,
        description="Доп. доля урона против целей конкретного размера, напр. алебарда {LARGE: 0.3, HUGE: 0.3}",
    )


class Equipment(BaseModel):
    """
    Базовая модель любого предмета экипировки.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ..., min_length=1, description="Уникальный ID (напр. human_weapon_halberd_02)"
    )
    name: str = Field(..., min_length=1, description="Название предмета")
    lore: str = Field(..., min_length=1, description="Лор предмета")

    slot: EquipmentSlot = Field(..., description="Слот экипировки")
    category: Optional[EquipmentCategoryType] = Field(
        default=None, description="Подтип предмета (оружие, броня, аксессуар)"
    )
    tags: set[EquipmentTag] = Field(
        default_factory=set, description="Набор механических и лорных тегов"
    )
    tier: int = Field(..., ge=0, le=6, description="Тир предмета (0-6)")

    # Каждый предмет выбирает, что будет давать юниту
    stats: EquipmentStats = Field(default_factory=EquipmentStats)

    # Экономика производства
    cost_gold: float = Field(default=0.0, ge=0)
    cost_material: float = Field(default=0.0, ge=0)

    is_custom: bool = Field(default=False, description="Создано ли оружейником-LLM")
    special_rules: Optional[str] = Field(
        default=None, description="Текстовое описание кастомных механик"
    )

    @model_validator(mode="after")
    def validate_category_matches_slot(self) -> "Equipment":
        if self.category is None:
            return self

        if self.slot == EquipmentSlot.WEAPON and not isinstance(self.category, WeaponCategory):
            raise InvalidEquipmentSlotError(
                item_id=self.id,
                expected_slot=EquipmentSlot.WEAPON.value,
                actual_slot=str(self.category),
            )
        if self.slot == EquipmentSlot.ARMOR and not isinstance(self.category, ArmorCategory):
            raise InvalidEquipmentSlotError(
                item_id=self.id,
                expected_slot=EquipmentSlot.ARMOR.value,
                actual_slot=str(self.category),
            )
        if self.slot == EquipmentSlot.ACCESSORY and not isinstance(
            self.category, AccessoryCategory
        ):
            raise InvalidEquipmentSlotError(
                item_id=self.id,
                expected_slot=EquipmentSlot.ACCESSORY.value,
                actual_slot=str(self.category),
            )
        return self

    def has_tag(self, tag: EquipmentTag) -> bool:
        """Проверяет наличие механического или лорного тега."""
        return tag in self.tags

    @property
    def is_two_handed(self) -> bool:
        return EquipmentTag.TWO_HANDED in self.tags

    @property
    def is_firearm(self) -> bool:
        return self.category == WeaponCategory.FIREARM or EquipmentTag.BLACKPOWDER in self.tags

    @property
    def is_braceable(self) -> bool:
        return EquipmentTag.BRACEABLE in self.tags
