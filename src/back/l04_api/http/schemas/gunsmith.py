"""
Схемы заказа оружейнику и карточки готового чертежа.
"""

from typing import Optional

from pydantic import BaseModel, Field

from src.back.l01_domain.army.models.card.equipment import Equipment


class BlueprintDraftRequest(BaseModel):
    """
    Заказ правителя оружейнику, сформулированный своими словами.
    """

    faction_id: str = Field(..., min_length=1)
    user_request: str = Field(..., min_length=1, max_length=4000)


class BlueprintDraftResponse(BaseModel):
    """
    Ответ мастера: чертеж и его реплика.

    draft пуст, если мастер отказался от заказа - причина отказа лежит
    в master_reply и показывается игроку как есть.
    """

    is_approved: bool = Field(...)
    master_reply: str = Field(default="")
    draft: Optional[Equipment] = Field(default=None)


class BlueprintApproveRequest(BaseModel):
    """
    Согласие игрока с чертежом: списывает разработку и кладет чертеж в арсенал.
    """

    faction_id: str = Field(..., min_length=1)
    draft: Equipment = Field(..., description="Чертеж, полученный из draft-эндпоинта")
