"""
Создание кастомных персонажей и оценка кризисов мира.

Отказ мастера от биографии - это его ответ, а не ошибка запроса: он
приезжает обычным 200 с пустым персонажем и объяснением в реплике.
"""

from fastapi import APIRouter

from src.back.l04_api.dependencies import GameMaster, World
from src.back.l04_api.http.schemas.game_master import (
    AdvisorResponse,
    CharacterRequest,
    CommanderResponse,
    HeroResponse,
    LordRequest,
    LordResponse,
    WorldEventResponse,
)

router = APIRouter(prefix="/game-master", tags=["game_master"])


# ====================================================
# Кастомные личности
# ====================================================


@router.post("/commanders", response_model=CommanderResponse)
async def create_commander(
    payload: CharacterRequest, game_master: GameMaster, world: World
) -> CommanderResponse:
    """Создает полководца по биографии и кладет его в пул найма."""
    commander, master_reply = await game_master.create_custom_commander(
        world_state=world,
        faction_id=payload.faction_id,
        biography_text=payload.biography_text,
    )
    return CommanderResponse(master_reply=master_reply, commander=commander)


@router.post("/heroes", response_model=HeroResponse)
async def create_hero(
    payload: CharacterRequest, game_master: GameMaster, world: World
) -> HeroResponse:
    """Создает героя по биографии и кладет его в пул найма."""
    hero, master_reply = await game_master.create_custom_hero(
        world_state=world,
        faction_id=payload.faction_id,
        biography_text=payload.biography_text,
    )
    return HeroResponse(master_reply=master_reply, hero=hero)


@router.post("/lords", response_model=LordResponse)
async def create_lord(
    payload: LordRequest, game_master: GameMaster, world: World
) -> LordResponse:
    """Создает лорда и при необходимости сажает его на трон фракции."""
    lord, master_reply = await game_master.create_custom_lord(
        world_state=world,
        faction_id=payload.faction_id,
        biography_text=payload.biography_text,
        assign_as_ruler=payload.assign_as_ruler,
    )
    return LordResponse(master_reply=master_reply, lord=lord)


@router.post("/advisors", response_model=AdvisorResponse)
async def create_advisor(
    payload: CharacterRequest, game_master: GameMaster, world: World
) -> AdvisorResponse:
    """Создает персонализированного советника для интерфейса."""
    advisor, master_reply = await game_master.create_custom_advisor(
        world_state=world,
        faction_id=payload.faction_id,
        biography_text=payload.biography_text,
    )
    return AdvisorResponse(master_reply=master_reply, advisor=advisor)


# ====================================================
# Кризисы мира
# ====================================================


@router.post("/events/evaluate", response_model=WorldEventResponse)
async def evaluate_world_events(
    game_master: GameMaster, world: World, force: bool = False
) -> WorldEventResponse:
    """
    Оценивает состояние партии и при необходимости роняет кризис.
    force игнорирует паузу между событиями (отладка и сценарные триггеры).
    """
    event = await game_master.evaluate_world_events(world_state=world, force=force)
    return WorldEventResponse(event=event)
