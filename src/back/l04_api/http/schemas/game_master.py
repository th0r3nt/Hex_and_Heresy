"""
Схемы генерации кастомных личностей и запроса событий мира.
"""

from typing import Optional

from pydantic import BaseModel, Field

from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.factions.models.lord import Lord
from src.back.l01_domain.world.models.events import GlobalEvent
from src.back.l02_services.mechanics.game_master.custom.advisers import CustomAdvisor


class CharacterRequest(BaseModel):
    """
    Биография персонажа, написанная игроком.
    """

    faction_id: str = Field(..., min_length=1)
    biography_text: str = Field(..., min_length=1, max_length=6000)


class LordRequest(CharacterRequest):
    """
    Биография лорда с указанием, садить ли его на трон фракции.
    """

    assign_as_ruler: bool = Field(default=True)


class CommanderResponse(BaseModel):
    """
    Ответ мастера игры о полководце.

    Персонаж пуст, если мастер отклонил биографию: объяснение лежит
    в master_reply и показывается игроку как есть.
    """

    master_reply: str = Field(default="")
    commander: Optional[Commander] = Field(default=None)


class HeroResponse(BaseModel):
    """Ответ мастера игры о герое."""

    master_reply: str = Field(default="")
    hero: Optional[Hero] = Field(default=None)


class LordResponse(BaseModel):
    """Ответ мастера игры о лорде."""

    master_reply: str = Field(default="")
    lord: Optional[Lord] = Field(default=None)


class AdvisorResponse(BaseModel):
    """Ответ мастера игры о советнике."""

    master_reply: str = Field(default="")
    advisor: Optional[CustomAdvisor] = Field(default=None)


class WorldEventResponse(BaseModel):
    """
    Результат оценки состояния партии мастером игры.
    """

    event: Optional[GlobalEvent] = Field(
        default=None, description="None, если кризис не назрел"
    )
