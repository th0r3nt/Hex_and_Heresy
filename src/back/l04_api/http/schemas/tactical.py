"""
Схемы тактического боя: развертывание, приказы отрядам и итоги раунда.
"""

from typing import Optional

from pydantic import BaseModel, Field

from src.back.l01_domain.combat.models.state import SquadOrder, TacticalBattleState
from src.back.l01_domain.maps.models.strategic import HexCoordinates


class BattleStartRequest(BaseModel):
    """
    Начало тактического боя.

    Расстановку и сетку готовит интерфейс, поэтому состояние боя приезжает
    целиком: сервер закрепляет за боем армии и переводит режим игры.
    """

    hex_coordinates: HexCoordinates = Field(..., description="Гекс глобальной карты")
    attacker_faction_id: str = Field(..., min_length=1)
    defender_faction_id: str = Field(..., min_length=1)
    battle_state: TacticalBattleState = Field(...)


class BattleOrdersRequest(BaseModel):
    """
    Пачка приказов отрядам на предстоящий раунд.

    Приказы копятся в состоянии боя и разбираются оркестратором в момент
    расчета раунда: стороны отдают приказы одновременно (WEGO).
    """

    orders: list[SquadOrder] = Field(default_factory=list)
    replace_pending: bool = Field(
        default=True,
        description="Сбросить ранее отданные приказы вместо добавления к ним",
    )


class BattleFinishRequest(BaseModel):
    """
    Закрытие боя и возврат на глобальную карту.
    """

    victor_faction_id: Optional[str] = Field(
        default=None, description="None при ничьей или обоюдном уничтожении"
    )
    is_base_destroyed: bool = Field(default=False)
