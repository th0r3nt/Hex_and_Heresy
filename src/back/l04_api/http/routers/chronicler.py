"""
Витрина летописи: страницы хроник, Зал павших и слухи.

Записи текущей партии живут в WorldState, записи прошлых партий - в базе,
поэтому архив читается отдельными эндпоинтами и без активной игры.
"""

from fastapi import APIRouter, Query

from src.back.l01_domain.world.constants import CHRONICLE_HISTORY_PAGE_SIZE
from src.back.l04_api.dependencies import Chronicler, World
from src.back.l04_api.http.schemas.chronicler import (
    ArchivePage,
    ChroniclePage,
    FallenPage,
    RumorsPage,
)

router = APIRouter(prefix="/chronicler", tags=["chronicler"])

PageLimit = Query(default=CHRONICLE_HISTORY_PAGE_SIZE, ge=1, le=200)


# ====================================================
# Текущая партия
# ====================================================


@router.get("/history", response_model=ChroniclePage)
async def get_history(
    chronicler: Chronicler, world: World, limit: int = PageLimit
) -> ChroniclePage:
    """Страницы летописи текущей партии."""
    return ChroniclePage(entries=chronicler.get_history(world, limit=limit))


@router.get("/fallen", response_model=FallenPage)
async def get_fallen(
    chronicler: Chronicler, world: World, limit: int = PageLimit
) -> FallenPage:
    """Надгробия Зала павших текущей партии."""
    return FallenPage(records=chronicler.get_fallen(world, limit=limit))


@router.get("/rumors", response_model=RumorsPage)
async def get_rumors(
    chronicler: Chronicler, world: World, limit: int = PageLimit
) -> RumorsPage:
    """Слухи, оброненные летописцем в окно логов."""
    return RumorsPage(rumors=chronicler.get_rumors(world, limit=limit))


# ====================================================
# Архив прошлых партий
# ====================================================


@router.get("/archive/history", response_model=ArchivePage)
async def get_archived_history(
    chronicler: Chronicler, limit: int = PageLimit
) -> ArchivePage:
    """Летописи прошлых партий - для меню вне активной игры."""
    return ArchivePage(items=await chronicler.get_archived_history(limit=limit))


@router.get("/archive/fallen", response_model=ArchivePage)
async def get_archived_fallen(
    chronicler: Chronicler, limit: int = PageLimit
) -> ArchivePage:
    """Павшие прошлых партий."""
    return ArchivePage(items=await chronicler.get_archived_fallen(limit=limit))
