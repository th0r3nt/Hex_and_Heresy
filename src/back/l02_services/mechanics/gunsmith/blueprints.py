"""
Фабрика сборки и внедрения кастомных чертежей.
"""

import uuid
from typing import Optional

from src.back.l01_domain.army.constants import AccessoryCategory, ArmorCategory, WeaponCategory
from src.back.l01_domain.army.models.card.equipment import Equipment, EquipmentStats
from src.back.l02_services.mechanics.gunsmith.crafting import LLMGunsmithResponse


class BlueprintRegistry:
    """
    Собирает валидный доменный объект Equipment из данных генерации.
    """

    @staticmethod
    def construct_draft(
        response: LLMGunsmithResponse,
        stats: EquipmentStats,
        cost_gold: float,
        cost_material: float,
    ) -> Equipment:
        # Генерируем короткий уникальный ID
        uid = f"eq_custom_{uuid.uuid4().hex[:8]}"

        # Определение категории по строке от LLM
        category: Optional[str] = None
        if response.category_name:
            # Ищем совпадение в Enum-ах
            cat_val = response.category_name.lower()
            for enum_cls in (WeaponCategory, ArmorCategory, AccessoryCategory):
                try:
                    category = enum_cls(cat_val)
                    break
                except ValueError:
                    continue

        return Equipment(
            id=uid,
            name=response.name or "Безымянный прототип",
            lore=response.lore or "Собрано в мастерской по индивидуальному заказу.",
            slot=response.slot,
            category=category,
            tags=set(response.tags),
            tier=response.tier or 1,
            stats=stats,
            cost_gold=cost_gold,
            cost_material=cost_material,
            is_custom=True,
            special_rules=response.special_rules,
        )
