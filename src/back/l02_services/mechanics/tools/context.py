"""
Обстановка, в которой исполняется вызов навыка.

Модель называет только то, что относится к делу: гекс, отряд, размер дани.
Кто именно отдает приказ, каким миром и каким боем - подставляет игра.
Иначе советнику людей ничего не стоило бы подвинуть ползунок налога
эльфам, просто указав чужой идентификатор в аргументах.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.world.models.state import WorldState


class ToolExecutionContext(BaseModel):
    """
    От чьего лица и над каким миром работает модель прямо сейчас.
    """

    # Мир и бой - живые изменяемые агрегаты, копировать их нельзя
    model_config = ConfigDict(arbitrary_types_allowed=True)

    world_state: WorldState = Field(..., description="Мир, который меняют навыки")
    faction_id: str = Field(
        ..., min_length=1, description="Держава, от лица которой говорит модель"
    )

    counterpart_faction_id: Optional[str] = Field(
        default=None,
        description="Собеседник в переговорах: чью просьбу рассматривает лорд",
    )
    ambassador_id: Optional[str] = Field(
        default=None, description="Посол, ведущий переговоры прямо сейчас"
    )
    battle_state: Optional[TacticalBattleState] = Field(
        default=None, description="Тактический бой, если приказы отдаются в нем"
    )


__all__ = ["ToolExecutionContext"]
