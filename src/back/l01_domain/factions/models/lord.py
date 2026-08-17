"""
Правитель фракции - определяет макро-стратегию (налоги, приоритеты
построек, дипломатическую позицию) и является "лицом" фракции в
дипломатии: именно к Lord'у приходят депеши и послы других фракций.
"""

from uuid import uuid4
from pydantic import BaseModel, Field

# TODO: проработать сильнее, придумать и добавить архетипы правителей
class Lord(BaseModel):
    """
    Правитель фракции.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    faction_id: str = Field(...)
    name: str = Field(..., min_length=1)
    title: str = Field(
        ..., description="напр. 'Эрцгерцог', 'Судья', 'Вождь', 'Магистр Инквизиции'"
    )
