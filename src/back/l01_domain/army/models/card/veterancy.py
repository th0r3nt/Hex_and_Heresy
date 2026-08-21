"""
Модель ветеранства и индивидуальной личности отряда.
"""

from typing import Optional
from pydantic import BaseModel, Field
from src.back.l01_domain.army.constants import (
    VETERANCY_KILL_WEIGHT_THRESHOLD,
    VETERANCY_SERVICE_DAYS_THRESHOLD,
)
from src.back.l01_domain.common import MechanicalModifier


class VeterancyStatus(BaseModel):
    """
    Данные Именного отряда.
    Заполняются, когда безымянный отряд совершает подвиг на поле боя,
    либо когда пересекает один из накопительных порогов — взвешенных
    убийств (accumulate_kills) или времени службы в армии под командованием
    полководца (accumulate_service). Оба метода только сигналят момент
    пересечения порога — фактическое присвоение личности (promote) остаётся
    за вызывающим кодом (Game Master / Chronicler).
    """

    is_named: bool = Field(default=False, description="Получил ли отряд имя и личность")
    commander_name: Optional[str] = Field(
        default=None, description="Имя командира (напр. Маркус)"
    )
    squad_nickname: Optional[str] = Field(
        default=None, description="Название отряда (напр. '7-й полк Маркуса')"
    )
    trait_name: Optional[str] = Field(default=None, description="Черта характера отряда")
    lore_description: Optional[str] = Field(
        default=None, description="Сгенерированная история подвига"
    )

    modifier: Optional[MechanicalModifier] = Field(
        default=None, description="Игровой бафф за подвиг"
    )

    # Требования ветеранов (могут повышать цену содержания через LLM)
    upkeep_gold_multiplier: float = Field(
        default=1.0, ge=1.0, description="Множитель жалования"
    )

    # История диалогов (хранится ID диалога или краткий контекст для LLM)
    dialog_context_id: Optional[str] = Field(default=None)

    # Накопительные пороги повышения (персистентны между боями и тактами)
    accumulated_kill_weight: float = Field(
        default=0.0,
        ge=0.0,
        description="Накопленный взвешенный урон по габаритам убитых юнитов",
    )
    accumulated_service_days: float = Field(
        default=0.0,
        ge=0.0,
        description="Накопленное время службы в армии под командованием полководца, в игровых сутках",
    )

    def promote(
        self,
        commander_name: str,
        squad_nickname: str,
        trait_name: str,
        lore: str,
        modifier: Optional[MechanicalModifier] = None,
    ) -> None:
        """
        Переводит отряд в статус Именного (Ветеран).
        """

        self.is_named = True
        self.commander_name = commander_name
        self.squad_nickname = squad_nickname
        self.trait_name = trait_name
        self.lore_description = lore
        self.modifier = modifier

    def accumulate_kills(self, weight: float) -> bool:
        """
        Прибавляет взвешенный урон по габариту убитых юнитов к накопителю.
        Возвращает True, если именно этим вызовом накопитель впервые
        пересёк VETERANCY_KILL_WEIGHT_THRESHOLD, иначе False — в том
        числе если порог был пройден одним из предыдущих вызовов.
        """

        if weight <= 0.0:
            return False

        was_below_threshold = self.accumulated_kill_weight < VETERANCY_KILL_WEIGHT_THRESHOLD
        self.accumulated_kill_weight += weight
        return (
            was_below_threshold
            and self.accumulated_kill_weight >= VETERANCY_KILL_WEIGHT_THRESHOLD
        )

    def accumulate_service(self, days: float) -> bool:
        """
        Прибавляет время службы в армии полководца (в игровых сутках) к
        накопителю. Возвращает True, если именно этим вызовом накопитель
        впервые пересёк VETERANCY_SERVICE_DAYS_THRESHOLD, иначе False.
        """

        if days <= 0.0:
            return False

        was_below_threshold = self.accumulated_service_days < VETERANCY_SERVICE_DAYS_THRESHOLD
        self.accumulated_service_days += days
        return (
            was_below_threshold
            and self.accumulated_service_days >= VETERANCY_SERVICE_DAYS_THRESHOLD
        )
