"""
Модели снимка партии: метаданные сохранения и готовый к записи снапшот.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.back.l01_domain.world.models.state import WorldState


class SaveMetadata(BaseModel):
    """
    Краткая сводка о сохранении для списков в главном меню.
    Не участвует в восстановлении партии, служит только для отображения.
    """

    model_config = ConfigDict(frozen=True)

    save_id: str = Field(..., min_length=1, description="UUID сохранения")
    save_name: str = Field(..., min_length=1, description="Пользовательское имя сейва")
    created_at: datetime = Field(..., description="Момент подготовки снимка (UTC)")

    total_ticks: int = Field(..., ge=0, description="Прожитых глобальных тактов")
    current_day: int = Field(..., ge=1, description="День цикла на момент снимка")
    current_year: int = Field(..., ge=1, description="Год на момент снимка")

    player_faction_name: Optional[str] = Field(
        default=None, description="Название фракции игрока (None для наблюдателя)"
    )
    factions_count: int = Field(..., ge=0, description="Число фракций в партии")
    armies_count: int = Field(..., ge=0, description="Число армий на глобальной карте")
    custom_equipment_count: int = Field(
        default=0, ge=0, description="Число уникальных чертежей Оружейника"
    )


class SaveSnapshot(BaseModel):
    """
    Готовый к записи снимок партии: метаданные плюс отвязанная копия WorldState.
    """

    metadata: SaveMetadata
    state: WorldState
