"""
Агрегат отряда (SquadCard) — ключевая боевая единица на тактической и глобальной карте.
"""

from uuid import uuid4
from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.army.constants import (
    MAX_MORALE,
    MIN_MORALE,
    MAX_STAMINA,
    MIN_STAMINA,
    PANIC_THRESHOLD_MORALE,
)
from src.back.l01_domain.army.models.card.unit import UnitArchetype
from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.army.models.card.veterancy import VeterancyStatus


class SquadState(BaseModel):
    """Динамическое состояние отряда в текущем бою или на ходу."""

    unit_count: int = Field(..., ge=0)
    hp_first_unit: float = Field(
        ..., ge=0, description="ХП самого переднего (получающего урон) бойца"
    )  # Нужно для цикла получения урона отрядом
    morale: float = Field(default=MAX_MORALE, ge=MIN_MORALE, le=MAX_MORALE)
    stamina: float = Field(default=MAX_STAMINA, ge=MIN_STAMINA, le=MAX_STAMINA)

    is_in_panic: bool = Field(default=False)
    is_exhausted: bool = Field(default=False)


class Squad(BaseModel):
    """
    Агрегат отряда.
    Собирается из: архетип + оружие + броня + аксессуар + ветеранство.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()), description="Уникальный UUID конкретного отряда"
    )
    archetype: UnitArchetype = Field(..., description="Базовый расовый юнит")

    # Модульное снаряжение
    weapon: Optional[Equipment] = Field(default=None)  # TODO Импортировать из equipment?
    armor: Optional[Equipment] = Field(default=None)
    accessory: Optional[Equipment] = Field(default=None)

    # Личность/Ветеранство
    veterancy: VeterancyStatus = Field(default_factory=VeterancyStatus)

    state: SquadState = Field(...)

    @classmethod
    def create_new(
        cls,
        archetype: UnitArchetype,
        weapon: Optional[Equipment] = None,
        armor: Optional[Equipment] = None,
        accessory: Optional[Equipment] = None,
        custom_unit_count: Optional[int] = None,
    ) -> "Squad":
        """
        Фабричный метод создания нового свежего отряда.
        """

        unit_count = custom_unit_count or archetype.default_unit_count
        initial_state = SquadState(
            unit_count=unit_count,
            morale=archetype.base_stats.base_morale,
            stamina=archetype.base_stats.base_stamina,
        )
        return cls(
            archetype=archetype,
            weapon=weapon,
            armor=armor,
            accessory=accessory,
            state=initial_state,
        )

    # ==================================================================
    # РАСЧЕТНЫЕ СВОЙСТВА
    # ==================================================================

    @property
    def display_name(self) -> str:
        """
        Имя отряда для UI (имя ветеранов или стандартное).
        """

        if self.veterancy.is_named and self.veterancy.squad_nickname:
            return self.veterancy.squad_nickname
        return self.archetype.name

    @property
    def total_effective_armor(self) -> float:
        """
        Итоговая броня одного бойца с учётом снаряжения.
        """

        bonus = 0.0
        if self.armor:
            bonus += self.armor.stats.armor_bonus
        if self.accessory:
            bonus += self.accessory.stats.armor_bonus
        return self.archetype.base_stats.base_armor + bonus

    @property
    def total_attack_damage(self) -> float:
        """
        Итоговый базовый урон одной атаки одного бойца.
        """

        dmg = 0.0
        if self.weapon:
            dmg += self.weapon.stats.damage
        if self.accessory:
            dmg += self.accessory.stats.damage
        return dmg

    @property
    def upkeep_gold(self) -> float:
        """
        Итоговое содержание золотом за такт для ВСЕГО отряда.
        """

        base = self.archetype.base_upkeep_gold * self.state.unit_count
        return base * self.veterancy.upkeep_gold_multiplier

    @property
    def upkeep_food(self) -> float:
        """
        Итоговое содержание провизией за такт для ВСЕГО отряда.
        """

        return self.archetype.base_upkeep_food * self.state.unit_count

    # ==================================================================
    # ДОМЕННЫЕ МЕТОДЫ ИЗМЕНЕНИЯ СОСТОЯНИЯ
    # ==================================================================

    def take_damage(self, raw_damage: float, armor_piercing: float = 0.0) -> int:
        """
        Наносит урон отряду с учётом брони.
        Возвращает количество погибших бойцов за эту атаку.
        """

        if self.state.unit_count <= 0 or raw_damage <= 0:
            return 0

        effective_armor = max(0.0, self.total_effective_armor - armor_piercing)
        net_damage = max(
            1.0, raw_damage - effective_armor
        )  # Минимум 1 урон при чистом попадании

        deaths = 0
        hp_per_unit = self.archetype.base_stats.max_hp

        while net_damage > 0 and self.state.unit_count > 0:
            if net_damage < self.state.hp_first_unit:
                self.state.hp_first_unit -= net_damage
                net_damage = 0
            else:
                net_damage -= self.state.hp_first_unit
                self.state.unit_count -= 1
                deaths += 1
                self.state.hp_first_unit = hp_per_unit

        if self.state.unit_count <= 0:
            self.state.unit_count = 0
            self.state.hp_first_unit = 0.0

        return deaths

    def apply_morale_shock(self, amount: float) -> None:
        """
        Уменьшает мораль и проверяет статус паники.
        """

        self.state.morale = max(MIN_MORALE, self.state.morale - amount)
        if self.state.morale <= PANIC_THRESHOLD_MORALE:
            self.state.is_in_panic = True

    def recover_morale(self, amount: float) -> None:
        """
        Восстанавливает мораль.
        """

        self.state.morale = min(MAX_MORALE, self.state.morale + amount)
        if self.state.morale > PANIC_THRESHOLD_MORALE:
            self.state.is_in_panic = False
