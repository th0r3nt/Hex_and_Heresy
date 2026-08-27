"""
Мост между корнем компоновки и роутерами.

Достает собранный контейнер из состояния приложения FastAPI и раздает
обработчикам готовые фасады. Ничего не создает сам: сборка графа
зависимостей целиком лежит на main.py.
"""

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request, status

from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.gameflow.facade import GameFlowFacade
from src.back.l02_services.mechanics.advisor.facade import AdvisorFacade
from src.back.l02_services.mechanics.chronicler.facade import ChroniclerFacade
from src.back.l02_services.mechanics.diplomacy.facade import DiplomacyFacade
from src.back.l02_services.mechanics.game_master.facade import GameMasterFacade
from src.back.l02_services.mechanics.gunsmith.facade import GunsmithFacade
from src.back.l02_services.saves.facade import SavesFacade
from src.back.l02_services.turns.facade import TurnsFacade
from src.back.l03_infrastructure.llm.facade import LLMFacade

if TYPE_CHECKING:
    # Импорт только для подсказок типов: main.py включает в себя роутеры,
    # а те - этот модуль, и обычный импорт замкнул бы круг
    from src.back.main import AppContainer


# ====================================================
# Контейнер
# ====================================================


def get_container(request: Request) -> "AppContainer":
    """
    Контейнер зависимостей, положенный в app.state при старте приложения.
    """
    return request.app.state.container


# ====================================================
# Фасады прикладного слоя
# ====================================================


def get_gameflow_facade(request: Request) -> GameFlowFacade:
    return get_container(request).gameflow_facade


def get_turns_facade(request: Request) -> TurnsFacade:
    return get_container(request).turns_facade


def get_saves_facade(request: Request) -> SavesFacade:
    return get_container(request).saves_facade


def get_diplomacy_facade(request: Request) -> DiplomacyFacade:
    return get_container(request).diplomacy_facade


def get_gunsmith_facade(request: Request) -> GunsmithFacade:
    return get_container(request).gunsmith_facade


def get_game_master_facade(request: Request) -> GameMasterFacade:
    return get_container(request).game_master_facade


def get_chronicler_facade(request: Request) -> ChroniclerFacade:
    return get_container(request).chronicler_facade


def get_advisor_facade(request: Request) -> AdvisorFacade:
    return get_container(request).advisor_facade


def get_llm_facade(request: Request) -> LLMFacade:
    return get_container(request).llm_facade


def get_event_bus(request: Request) -> EventBusProtocol:
    return get_container(request).event_bus


# ====================================================
# Состояние активной партии
# ====================================================


def get_world_state(request: Request) -> WorldState:
    """
    Мир текущей партии.

    Партия живет в GameFlowFacade: корень компоновки привязывает мир туда
    сразу после старта или загрузки. Пока партии нет, любой игровой запрос
    бессмыслен - отсюда явная ошибка вместо None.
    """
    world_state = get_gameflow_facade(request).world_state
    if world_state is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Активная партия не начата: начните новую игру или загрузите сохранение.",
        )
    return world_state


def get_battle_state(request: Request) -> TacticalBattleState:
    """
    Состояние идущего тактического боя.
    """
    battle_state = get_gameflow_facade(request).active_battle_state
    if battle_state is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Тактический бой не идет.",
        )
    return battle_state


# ====================================================
# Псевдонимы для аннотаций обработчиков
# ====================================================

GameFlow = Annotated[GameFlowFacade, Depends(get_gameflow_facade)]
Turns = Annotated[TurnsFacade, Depends(get_turns_facade)]
Saves = Annotated[SavesFacade, Depends(get_saves_facade)]
Diplomacy = Annotated[DiplomacyFacade, Depends(get_diplomacy_facade)]
Gunsmith = Annotated[GunsmithFacade, Depends(get_gunsmith_facade)]
GameMaster = Annotated[GameMasterFacade, Depends(get_game_master_facade)]
Chronicler = Annotated[ChroniclerFacade, Depends(get_chronicler_facade)]
Advisor = Annotated[AdvisorFacade, Depends(get_advisor_facade)]
LLM = Annotated[LLMFacade, Depends(get_llm_facade)]
World = Annotated[WorldState, Depends(get_world_state)]
Battle = Annotated[TacticalBattleState, Depends(get_battle_state)]
