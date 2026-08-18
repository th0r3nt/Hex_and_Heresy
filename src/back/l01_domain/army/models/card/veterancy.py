"""
Модель ветеранства и индивидуальной личности отряда.
"""

from typing import Optional
from pydantic import BaseModel, Field
from src.back.l01_domain.common import MechanicalModifier


class VeterancyStatus(BaseModel):
    """
    Данные Именного отряда.
    Заполняются, когда безымянный отряд совершает подвиг на поле боя.
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
