"""
Сохранение, загрузка, удаление и список сейвов.

Право на запись в текущем режиме проверяет игровой поток
(assert_can_save), целостность снимка - фасад сохранений.
"""

from fastapi import APIRouter, Request

from src.back.l01_domain.world.models.saves import SaveMetadata
from src.back.l04_api.dependencies import GameFlow, Saves, World, get_container
from src.back.l04_api.http.schemas.common import OperationResult
from src.back.l04_api.http.schemas.saves import (
    SaveExistsResponse,
    SaveGameRequest,
    SaveSlotResponse,
)

router = APIRouter(prefix="/saves", tags=["saves"])


# ====================================================
# Витрина сохранений
# ====================================================


@router.get("", response_model=SaveSlotResponse)
async def list_saves(saves: Saves) -> SaveSlotResponse:
    """Список сохранений для меню загрузки."""
    return SaveSlotResponse(items=await saves.list_saves())


@router.get("/{save_id}/exists", response_model=SaveExistsResponse)
async def has_save(save_id: str, saves: Saves) -> SaveExistsResponse:
    """Наличие слота - чтобы погасить кнопку «Продолжить»."""
    return SaveExistsResponse(save_id=save_id, exists=await saves.has_save(save_id))


# ====================================================
# Запись снимка
# ====================================================


@router.post("", response_model=SaveMetadata)
async def save_game(
    payload: SaveGameRequest, saves: Saves, gameflow: GameFlow, world: World
) -> SaveMetadata:
    """Записывает снимок партии в новый или указанный слот."""
    gameflow.assert_can_save()
    return await saves.save_game(
        world_state=world,
        save_name=payload.save_name,
        save_id=payload.save_id,
    )


@router.post("/quick", response_model=SaveMetadata)
async def quick_save(saves: Saves, gameflow: GameFlow, world: World) -> SaveMetadata:
    """Перезаписывает слот быстрого сохранения."""
    gameflow.assert_can_save()
    return await saves.quick_save(world)


# ====================================================
# Подъем партии
# ====================================================


@router.post("/{save_id}/load", response_model=OperationResult)
async def load_game(save_id: str, request: Request, saves: Saves) -> OperationResult:
    """
    Поднимает партию из сохранения и делает ее активной.

    Разослать восстановленный мир по сервисам - работа корня компоновки:
    он один знает состав контейнера, поэтому обработчик передает сессию ему.
    """
    container = get_container(request)

    session = await saves.load_game(save_id)
    await container.gameflow_facade.load_game()
    container.bind_session(session)

    return OperationResult(detail=f"Партия из сохранения '{save_id}' загружена.")


# ====================================================
# Удаление
# ====================================================


@router.delete("/{save_id}", response_model=OperationResult)
async def delete_save(save_id: str, saves: Saves) -> OperationResult:
    """Удаляет слот. Отсутствие записи ошибкой не считается."""
    is_deleted = await saves.delete_save(save_id)
    return OperationResult(
        success=is_deleted,
        detail=(
            f"Сохранение '{save_id}' удалено."
            if is_deleted
            else f"Сохранения '{save_id}' не существовало."
        ),
    )
