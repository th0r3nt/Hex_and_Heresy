"""
Типизированные контексты данных, сопровождающие переходы конечного автомата
игрового процесса.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.events import GlobalEvent


class CombatTransitionPayload(BaseModel):
    """Данные для инициализации тактического боя."""

    model_config = ConfigDict(frozen=True)

    hex_coordinates: HexCoordinates = Field(
        ..., description="Гекс глобальной карты, где начался бой"
    )
    attacker_faction_id: str = Field(..., min_length=1)
    defender_faction_id: str = Field(..., min_length=1)
    battle_state: TacticalBattleState = Field(
        ..., description="Инициализированное состояние тактического боя"
    )


class CombatResolutionPayload(BaseModel):
    """Данные об итогах завершенного тактического боя."""

    model_config = ConfigDict(frozen=True)

    battle_id: str = Field(..., min_length=1)
    victor_faction_id: Optional[str] = Field(
        default=None, description="None при ничьей или обоюдном уничтожении"
    )
    is_base_destroyed: bool = Field(
        default=False, description="Была ли разрушена база защитника"
    )


class DiplomacyTransitionPayload(BaseModel):
    """Данные для открытия экрана переговоров или аудиенции."""

    model_config = ConfigDict(frozen=True)

    initiator_faction_id: str = Field(..., min_length=1)
    target_faction_id: str = Field(..., min_length=1)
    ambassador_id: Optional[str] = Field(
        default=None, description="ID посла при личной встрече"
    )


class GlobalEventTransitionPayload(BaseModel):
    """Данные для отображения активного кризиса или события."""

    model_config = ConfigDict(frozen=True)

    event: GlobalEvent = Field(...)


class GameOverPayload(BaseModel):
    """Данные об окончании партии."""

    model_config = ConfigDict(frozen=True)

    is_player_victorious: bool = Field(...)
    reason: str = Field(
        ..., min_length=1, description="Причина окончания игры (напр. гибель цитадели)"
    )
    total_ticks_survived: int = Field(default=0, ge=0)
