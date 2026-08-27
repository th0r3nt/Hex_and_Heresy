"""
Схемы сохранений: метаданные слотов и команды записи/подъема партии.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class SaveGameRequest(BaseModel):
    """
    Запись снимка партии. Без save_id создается новый слот.
    """

    save_name: str = Field(..., min_length=1, max_length=120)
    save_id: Optional[str] = Field(
        default=None, description="Перезаписываемый слот; None - новая запись"
    )


class SaveSlotResponse(BaseModel):
    """
    Строка списка сохранений для меню загрузки.
    """

    items: list[dict[str, Any]] = Field(default_factory=list)


class SaveExistsResponse(BaseModel):
    """
    Наличие слота - чтобы погасить кнопку «Продолжить».
    """

    save_id: str = Field(...)
    exists: bool = Field(...)
