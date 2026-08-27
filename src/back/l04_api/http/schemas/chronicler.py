"""
Схемы витрины летописи: страницы хроник, надгробия и слухи.
"""

from typing import Any

from pydantic import BaseModel, Field

from src.back.l01_domain.world.models.chronicle import (
    ChronicleEntry,
    FallenRecord,
    RumorEntry,
)


class ChroniclePage(BaseModel):
    """Страницы летописи текущей партии."""

    entries: list[ChronicleEntry] = Field(default_factory=list)


class FallenPage(BaseModel):
    """Надгробия Зала павших текущей партии."""

    records: list[FallenRecord] = Field(default_factory=list)


class RumorsPage(BaseModel):
    """Слухи, оброненные летописцем в окно логов."""

    rumors: list[RumorEntry] = Field(default_factory=list)


class ArchivePage(BaseModel):
    """
    Летописи прошлых партий из базы: читаются из меню, вне активной игры,
    поэтому приезжают сырыми записями хранилища.
    """

    items: list[dict[str, Any]] = Field(default_factory=list)
