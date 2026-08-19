"""
Модели динамических глобальных и локальных событий мира.
"""

from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict

from src.back.l01_domain.common import MechanicalModifier
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.constants import GlobalEventCategory, GlobalEventScope


class GlobalEvent(BaseModel):
    """
    Глобальное или региональное событие, сгенерированное мастером игры.
    Накладывает механические эффекты на фракции или зоны карты.
    """

    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., min_length=1, description="Название события")
    description: str = Field(
        ..., min_length=1, description="Художественное описание для игрока"
    )

    category: GlobalEventCategory = Field(...)
    scope: GlobalEventScope = Field(default=GlobalEventScope.GLOBAL)

    # Целевые фильтры действия
    target_faction_ids: list[str] = Field(
        default_factory=list, description="ID фракций, если область действия ограничена"
    )
    target_hex_coords: list[HexCoordinates] = Field(
        default_factory=list, description="Координаты гексов, если событие локальное"
    )

    # Длительность в глобальных тактах (None = бессрочно до снятия триггером)
    duration_ticks_remaining: Optional[int] = Field(default=None, ge=0)
    is_active: bool = Field(default=True)

    modifiers: list[MechanicalModifier] = Field(
        default_factory=list, description="Список механических модификаторов события"
    )

    def tick(self) -> None:
        """
        Уменьшает оставшееся время действия события на 1 такт.
        """
        if not self.is_active or self.duration_ticks_remaining is None:
            return

        if self.duration_ticks_remaining > 0:
            self.duration_ticks_remaining -= 1

        if self.duration_ticks_remaining == 0:
            self.is_active = False

    def affects_faction(self, faction_id: str) -> bool:
        """
        Проверяет, распространяется ли событие на указанную фракцию.
        """
        if not self.is_active:
            return False
        if self.scope == GlobalEventScope.GLOBAL:
            return True
        return faction_id in self.target_faction_ids

    def affects_hex(self, coord: HexCoordinates) -> bool:
        """
        Проверяет, распространяется ли событие на указанный гекс карты.
        """
        if not self.is_active:
            return False
        if self.scope == GlobalEventScope.GLOBAL:
            return True
        return coord in self.target_hex_coords
