"""
Состояния игры и триггеры переходов конечного автомата.

Типизированные контексты переходов живут в домене:
`src.back.l01_domain.world.models.gameflow`.
"""

from enum import Enum


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
