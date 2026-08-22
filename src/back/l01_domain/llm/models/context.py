"""
Блок изменчивого контекста, уезжающего в промпт языковой модели.
"""

from pydantic import BaseModel, ConfigDict, Field


class ContextBlock(BaseModel):
    """
    Именованный кусок контекста. Пустое тело означает, что блоку нечего сказать,
    и он не попадет в промпт.
    """

    model_config = ConfigDict(frozen=True)

    title: str = Field(..., min_length=1, description="Заголовок блока в промпте")
    body: str = Field(default="", description="Содержимое блока")

    @property
    def is_empty(self) -> bool:
        return not self.body.strip()
