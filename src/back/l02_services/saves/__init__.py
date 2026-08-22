"""
Логика сохранений и загрузок состояния игры и фракций. Сохраняет в базу данных и загружает из нее.
"""

from src.back.l01_domain.world.models.saves import SaveMetadata, SaveSnapshot
from src.back.l02_services.saves.dumper import WorldStateDumper
from src.back.l02_services.saves.facade import AUTOSAVE_ID, QUICK_SAVE_ID, SavesFacade
from src.back.l02_services.saves.loader import (
    GameDataRepositoryFactory,
    LoadedSession,
    WorldStateLoader,
)

__all__ = [
    "AUTOSAVE_ID",
    "QUICK_SAVE_ID",
    "GameDataRepositoryFactory",
    "LoadedSession",
    "SaveMetadata",
    "SaveSnapshot",
    "SavesFacade",
    "WorldStateDumper",
    "WorldStateLoader",
]
