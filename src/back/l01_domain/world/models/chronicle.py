"""
Записи летописца: хроники сражений, некрологи Зала павших и фоновые слухи.

Эти модели - конечный продукт механики: они уезжают и в базу данных
(ChroniclerRepositoryProtocol), и на фронтенд, который рендерит из них свиток,
страницу Зала павших и строку в окне логов.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.world.constants import (
    CHRONICLE_BODY_MAX_LENGTH,
    CHRONICLE_QUOTE_MAX_LENGTH,
    CHRONICLE_TITLE_MAX_LENGTH,
    RUMOR_TEXT_MAX_LENGTH,
    VictoryType,
)
from src.back.l01_domain.world.models.battle_log import SquadBattleLog


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(text: str, limit: int) -> str:
    """
    Подрезает разговорившуюся модель до лимита интерфейса.

    Обрезка мягкая, а не отказ валидации: длинный, но живой текст лучше
    несостоявшейся летописи - перегенерировать бой будет уже не по чему.
    """
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 1].rstrip() + "…"


# ==================================================================
# ОТВЕТЫ ЯЗЫКОВОЙ МОДЕЛИ
# ==================================================================


class LLMChronicleResponse(BaseModel):
    """
    Ожидаемый JSON-ответ летописца о сражении (см. chronicler.md).
    """

    title: str = Field(..., description="Название сражения в летописи")
    quote: str = Field(default="", description="Хлесткая цитата эпохи под заголовком")
    body: str = Field(..., description="Художественный пересказ боя")

    @field_validator("title")
    @classmethod
    def _clamp_title(cls, value: str) -> str:
        return _clamp(value, CHRONICLE_TITLE_MAX_LENGTH)

    @field_validator("quote")
    @classmethod
    def _clamp_quote(cls, value: str) -> str:
        return _clamp(value, CHRONICLE_QUOTE_MAX_LENGTH)

    @field_validator("body")
    @classmethod
    def _clamp_body(cls, value: str) -> str:
        return _clamp(value, CHRONICLE_BODY_MAX_LENGTH)


class LLMFinaleResponse(BaseModel):
    """
    Ожидаемый JSON-ответ летописца о финале партии: ода триумфатору или
    реквием погибшей державе.
    """

    title: str = Field(..., description="Заголовок финальной главы летописи")
    body: str = Field(..., description="Ода или реквием - чем закончилась партия")

    @field_validator("title")
    @classmethod
    def _clamp_title(cls, value: str) -> str:
        return _clamp(value, CHRONICLE_TITLE_MAX_LENGTH)

    @field_validator("body")
    @classmethod
    def _clamp_body(cls, value: str) -> str:
        return _clamp(value, CHRONICLE_BODY_MAX_LENGTH)


class LLMEpitaphResponse(BaseModel):
    """
    Ожидаемый JSON-ответ летописца о погибшем именном отряде или герое.
    """

    title: str = Field(..., description="Заголовок надгробия в Зале павших")
    epitaph: str = Field(..., description="Некролог: как жили и как полегли")

    @field_validator("title")
    @classmethod
    def _clamp_title(cls, value: str) -> str:
        return _clamp(value, CHRONICLE_TITLE_MAX_LENGTH)

    @field_validator("epitaph")
    @classmethod
    def _clamp_epitaph(cls, value: str) -> str:
        return _clamp(value, CHRONICLE_BODY_MAX_LENGTH)


# ==================================================================
# КОГО ХОРОНЯТ
# ==================================================================


class FallenKind(str, Enum):
    """Кем был павший при жизни."""

    SQUAD = "squad"
    HERO = "hero"


class FallenSubject(BaseModel):
    """
    Заявка на надгробие: все, что летописец должен знать о павшем.

    Отряды и герои гибнут по-разному, но эпитафия пишется одинаково, поэтому
    обе механики приводят своих мертвых к этому виду.
    """

    model_config = ConfigDict(frozen=True)

    subject_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    kind: FallenKind = Field(default=FallenKind.SQUAD)

    race: FactionRace = Field(...)
    faction_id: Optional[str] = Field(default=None)
    commander_name: Optional[str] = Field(default=None)
    archetype_name: str = Field(default="")

    initial_count: int = Field(default=0, ge=0, description="Сколько их было")
    kills: int = Field(default=0, ge=0, description="Скольких забрали с собой")
    killer_name: str = Field(default="", description="Кто их положил")

    @classmethod
    def from_squad_log(cls, log: SquadBattleLog, killer_name: str = "") -> "FallenSubject":
        return cls(
            subject_id=log.squad_id,
            name=log.display_name,
            kind=FallenKind.SQUAD,
            race=log.race,
            faction_id=log.faction_id,
            commander_name=log.commander_name,
            archetype_name=log.archetype_name,
            initial_count=log.initial_count,
            kills=log.kills,
            killer_name=killer_name,
        )


# ==================================================================
# ЗАПИСИ ЛЕТОПИСИ
# ==================================================================


class ChronicleEntry(BaseModel):
    """
    Страница летописи об одном сражении.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    battle_id: str = Field(..., min_length=1, description="Бой, о котором написана страница")

    title: str = Field(..., min_length=1)
    quote: str = Field(default="")
    body: str = Field(..., min_length=1)

    tick: int = Field(default=0, ge=0, description="Глобальный такт, которым датирована запись")
    location_name: str = Field(default="", description="Где это случилось")
    faction_id: Optional[str] = Field(
        default=None, description="Фракция, чьими глазами написана страница"
    )
    created_at: datetime = Field(default_factory=_utc_now)

    @classmethod
    def from_response(
        cls,
        response: LLMChronicleResponse,
        battle_id: str,
        tick: int,
        location_name: str,
        faction_id: Optional[str] = None,
    ) -> "ChronicleEntry":
        """
        Собирает страницу летописи из ответа языковой модели.
        """
        return cls(
            battle_id=battle_id,
            title=response.title,
            quote=response.quote,
            body=response.body,
            tick=tick,
            location_name=location_name,
            faction_id=faction_id,
        )


class FallenRecord(BaseModel):
    """
    Надгробие Зала павших: именной отряд или герой, не переживший бой.

    Хранится вечно и переживает саму партию - игрок заходит сюда на сотом
    такте перечитывать эпитафии.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    squad_id: str = Field(..., min_length=1, description="ID отряда или героя")
    squad_name: str = Field(..., min_length=1, description="Имя, под которым его запомнили")
    commander_name: Optional[str] = Field(default=None)
    race: FactionRace = Field(...)
    faction_id: Optional[str] = Field(default=None)

    title: str = Field(default="", description="Заголовок надгробия")
    epitaph: str = Field(..., min_length=1, description="Некролог от летописца")

    death_tick: int = Field(default=0, ge=0)
    battle_id: Optional[str] = Field(default=None, description="Бой, в котором отряд полег")
    killer_name: str = Field(default="", description="Кто их положил")
    kills_earned: int = Field(default=0, ge=0, description="Скольких забрали с собой")
    created_at: datetime = Field(default_factory=_utc_now)

    @classmethod
    def from_response(
        cls,
        response: LLMEpitaphResponse,
        subject: FallenSubject,
        death_tick: int,
        battle_id: Optional[str] = None,
    ) -> "FallenRecord":
        """
        Собирает надгробие из ответа языковой модели и данных о павшем.
        """
        return cls(
            squad_id=subject.subject_id,
            squad_name=subject.name,
            commander_name=subject.commander_name,
            race=subject.race,
            faction_id=subject.faction_id,
            title=response.title,
            epitaph=response.epitaph,
            death_tick=death_tick,
            battle_id=battle_id,
            killer_name=subject.killer_name,
            kills_earned=subject.kills,
        )


class FinaleChronicle(BaseModel):
    """
    Последняя страница летописи: чем закончилась партия.

    Пишется однажды и живет в самом мире, поэтому переживает перезагрузку
    сохранения: экран финала должен читаться и после возвращения в игру.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid4()))

    is_player_victorious: bool = Field(...)
    victory_type: Optional[VictoryType] = Field(
        default=None, description="Ветка победы. None у поражения"
    )
    reason: str = Field(
        ..., min_length=1, description="Сухая причина финала - она же подпись на экране"
    )

    title: str = Field(default="", description="Заголовок финальной главы")
    body: str = Field(default="", description="Текст летописца. Пуст, если модель молчала")

    tick: int = Field(default=0, ge=0, description="Такт, которым датирован финал")
    faction_id: Optional[str] = Field(
        default=None, description="Фракция, чьими глазами написан финал"
    )
    created_at: datetime = Field(default_factory=_utc_now)

    @classmethod
    def from_response(
        cls,
        response: LLMFinaleResponse,
        is_player_victorious: bool,
        reason: str,
        victory_type: Optional[VictoryType] = None,
        tick: int = 0,
        faction_id: Optional[str] = None,
    ) -> "FinaleChronicle":
        """
        Собирает финальную главу из ответа языковой модели.
        """
        return cls(
            is_player_victorious=is_player_victorious,
            victory_type=victory_type,
            reason=reason,
            title=response.title,
            body=response.body,
            tick=tick,
            faction_id=faction_id,
        )


class RumorEntry(BaseModel):
    """
    Короткая атмосферная фраза в окно логов, когда боев не было несколько тактов.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str = Field(..., min_length=1)
    tick: int = Field(default=0, ge=0)
    faction_id: Optional[str] = Field(
        default=None, description="Фракция, до чьих ушей дошел слух"
    )
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("text")
    @classmethod
    def _clamp_text(cls, value: str) -> str:
        return _clamp(value, RUMOR_TEXT_MAX_LENGTH)
