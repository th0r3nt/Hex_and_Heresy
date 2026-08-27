"""
Роутеры HTTP. Каждый изолирован и работает ровно с одним фасадом l02_services.

Здесь же они собираются в единый api_router, который корню компоновки
остается только подключить к приложению.
"""

from fastapi import APIRouter

from src.back.l04_api.http.routers import (
    advisor,
    chronicler,
    diplomacy,
    game_master,
    gameflow,
    gunsmith,
    saves,
    settings,
    strategic,
    tactical,
)

api_router = APIRouter(prefix="/api")

for module in (
    gameflow,
    saves,
    strategic,
    tactical,
    diplomacy,
    gunsmith,
    game_master,
    chronicler,
    advisor,
    settings,
):
    api_router.include_router(module.router)

__all__ = ["api_router"]
