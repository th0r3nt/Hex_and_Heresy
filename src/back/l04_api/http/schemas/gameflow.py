"""
Схемы переходов конечного автомата и экрана окончания партии.
"""

from typing import Optional

from pydantic import BaseModel, Field

from src.back.l02_services.gameflow.states import GameState


class GameStateResponse(BaseModel):
    """
    Текущий режим игры для интерфейса.
    """

    state: GameState = Field(..., description="Активное состояние конечного автомата")
    is_party_active: bool = Field(
        default=False, description="Привязан ли к игре мир активной партии"
    )


class GameOverRequest(BaseModel):
    """
    Фиксация финала партии.
    """

    is_player_victorious: bool = Field(...)
    reason: str = Field(..., min_length=1, description="Причина окончания партии")
    total_ticks: int = Field(default=0, ge=0)


class GlobalEventScreenRequest(BaseModel):
    """
    Открытие модального окна кризиса по уже существующему событию мира.
    """

    event_id: str = Field(..., min_length=1)


class DiplomaticSessionRequest(BaseModel):
    """
    Открытие окна дипломатической аудиенции.
    """

    initiator_faction_id: str = Field(..., min_length=1)
    target_faction_id: str = Field(..., min_length=1)
    ambassador_id: Optional[str] = Field(default=None)
