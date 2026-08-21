"""
Состояния игры, триггеры переходов и типизированные контексты данных.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.events import GlobalEvent


class GameState(str, Enum):
    """Высокоуровневые состояния игрового процесса."""

    MAIN_MENU = "main_menu"  # Главное меню до загрузки или старта партии
    STRATEGIC_MAP = "strategic_map"  # Основной стратегический режим глобальной карты
    TACTICAL_COMBAT = "tactical_combat"  # Тактический бой на сеточной карте
    DIPLOMATIC_SESSION = (
        "diplomatic_session"  # Активная дипломатическая аудиенция или переговоры
    )
    GLOBAL_EVENT_RESOLUTION = (
        "global_event_resolution"  # Модальное окно выбора реакции на событие мастера игры
    )
    PAUSE = "pause"  # Внутриигровая пауза
    SETTINGS = "settings"  # Экран настроек
    CREDITS = "credits"  # Экран авторов/титров разработки
    GAME_OVER = "game_over"  # Экран финала партии (победа или поражение)


class GameFlowTrigger(str, Enum):
    """Триггеры и события, инициирующие смену состояния конечного автомата."""

    START_NEW_GAME = "start_new_game"
    LOAD_SAVED_GAME = "load_saved_game"
    ENGAGE_COMBAT = "engage_combat"
    RESOLVE_COMBAT = "resolve_combat"
    OPEN_AUDIENCE = "open_audience"
    CLOSE_AUDIENCE = "close_audience"
    TRIGGER_GLOBAL_EVENT = "trigger_global_event"
    RESOLVE_GLOBAL_EVENT = "resolve_global_event"
    PAUSE_GAME = "pause_game"
    RESUME_GAME = "resume_game"
    OPEN_SETTINGS = "open_settings"
    CLOSE_SETTINGS = "close_settings"
    OPEN_CREDITS = "open_credits"
    CLOSE_CREDITS = "close_credits"
    DECLARE_GAME_OVER = "declare_game_over"
    QUIT_TO_MAIN_MENU = "quit_to_main_menu"


# ==================================================================
# КОНТЕКСТЫ ДАННЫХ ПЕРЕХОДОВ
# ==================================================================


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
