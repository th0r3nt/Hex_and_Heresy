"""
Модели советника: окно предложения с кнопками выбора, ответ в свободном
диалоге и намерение советника, выраженное вызовом игрового навыка.

Советник работает в двух режимах (см. docs/game_mechanics/advisor.md):
предложение по своей инициативе между ходами и ответ на вопрос игрока.
Само действие он совершает уже после выбора игрока - отдельным вызовом
навыков Function Calling, поэтому в самом предложении параметров действия
нет: там только текст и кнопки.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from src.back.l01_domain.exceptions.advisor import AdvisorOptionNotFoundError

# Лимиты интерфейса: окно советника не безгранично, так что полезно ограничить символы
ADVISOR_TITLE_MAX_LENGTH = 80
ADVISOR_MESSAGE_MAX_LENGTH = 700

ADVISOR_OPTION_LABEL_MAX_LENGTH = 48
ADVISOR_MAX_OPTIONS = 4


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(text: str, limit: int) -> str:
    """
    Подрезает разговорившуюся модель до лимита интерфейса.

    Обрезка мягкая, а не отказ валидации: длинный, но осмысленный совет
    лучше несостоявшегося предложения.
    """
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 1].rstrip() + "…"


# ====================================================
# Варианты ответа игрока
# ====================================================


class AdvisorOptionKind(str, Enum):
    """
    Смысл кнопки под предложением советника.

    Механику определяет именно вид, а не подпись: по нему интерфейс рисует
    кнопку, а фасад понимает, нужно ли спрашивать у игрока текст.
    """

    ACCEPT = "accept"  # Принять
    ADJUST = "adjust"  # Смягченный или усиленный вариант
    DECLINE = "decline"  # Отклонить
    FREEFORM = "freeform"  # Дать свой ответ: игрок пишет своими словами


class AdvisorOption(BaseModel):
    """
    Один вариант ответа игрока на предложение советника.
    """

    id: str = Field(default_factory=lambda: f"opt_{uuid4().hex[:8]}")
    label: str = Field(..., min_length=1, description="Подпись кнопки в интерфейсе")
    kind: AdvisorOptionKind = Field(default=AdvisorOptionKind.ACCEPT)

    @field_validator("label")
    @classmethod
    def _clamp_label(cls, value: str) -> str:
        return _clamp(value, ADVISOR_OPTION_LABEL_MAX_LENGTH)

    @property
    def requires_player_text(self) -> bool:
        """Нужно ли открыть игроку поле ввода вместо немедленного действия."""
        return self.kind == AdvisorOptionKind.FREEFORM

    @property
    def is_refusal(self) -> bool:
        """Отказ закрывает предложение, не запуская исполнителя."""
        return self.kind == AdvisorOptionKind.DECLINE


# ====================================================
# Предложение советника
# ====================================================


class AdvisorProposal(BaseModel):
    """
    Окно предложения: реплика советника и кнопки выбора под ней.

    Предложение живет ровно до ответа игрока и в сохранение не уезжает:
    совет, данный десять тактов назад, к моменту загрузки уже неактуален.
    """

    id: str = Field(default_factory=lambda: f"advp_{uuid4().hex[:8]}")
    faction_id: str = Field(..., min_length=1)
    tick: int = Field(
        default=0, ge=0, description="Глобальный такт, на котором подан совет"
    )

    title: str = Field(..., min_length=1, description="Заголовок окна советника")
    message: str = Field(..., min_length=1, description="Что советник говорит правителю")
    options: list[AdvisorOption] = Field(..., min_length=1)

    created_at: datetime = Field(default_factory=_utc_now)
    chosen_option_id: Optional[str] = Field(default=None)

    @field_validator("title")
    @classmethod
    def _clamp_title(cls, value: str) -> str:
        return _clamp(value, ADVISOR_TITLE_MAX_LENGTH)

    @field_validator("message")
    @classmethod
    def _clamp_message(cls, value: str) -> str:
        return _clamp(value, ADVISOR_MESSAGE_MAX_LENGTH)

    @field_validator("options")
    @classmethod
    def _limit_options(cls, options: list[AdvisorOption]) -> list[AdvisorOption]:
        """
        Кнопок не больше, чем влезает в окно: лишние варианты модель придумала
        сверх контракта интерфейса.
        """
        return options[:ADVISOR_MAX_OPTIONS]

    @property
    def is_answered(self) -> bool:
        return self.chosen_option_id is not None

    def get_option(self, option_id: str) -> Optional[AdvisorOption]:
        return next((option for option in self.options if option.id == option_id), None)

    def choose(self, option_id: str) -> AdvisorOption:
        """
        Фиксирует выбор игрока и возвращает выбранный вариант.
        """
        option = self.get_option(option_id)
        if option is None:
            raise AdvisorOptionNotFoundError(proposal_id=self.id, option_id=option_id)

        self.chosen_option_id = option.id
        return option


# ====================================================
# Действия советника
# ====================================================


class AdvisorAction(BaseModel):
    """
    Намерение советника, выраженное вызовом игрового навыка.

    Аргументы намеренно оставлены свободным словарем: схемы навыков еще не
    описаны, и фиксировать здесь их поля значило бы придумывать контракт раньше времени.
    """

    tool_name: str = Field(..., min_length=1, description="Имя навыка Function Calling")
    arguments: dict[str, Any] = Field(default_factory=dict)


class AdvisorActionStatus(str, Enum):
    """Судьба одного намерения советника у исполнителя."""

    EXECUTED = "executed"
    NOT_SUPPORTED = "not_supported"  # Навык еще не подключен к исполнителю
    FAILED = "failed"  # Навык есть, но мир его не принял


class AdvisorActionOutcome(BaseModel):
    """Что исполнитель сделал с одним намерением советника."""

    action: AdvisorAction = Field(...)
    status: AdvisorActionStatus = Field(...)
    detail: str = Field(default="", description="Объяснение для игрока")

    @property
    def is_executed(self) -> bool:
        return self.status == AdvisorActionStatus.EXECUTED


class AdvisorDecision(BaseModel):
    """
    Итог выбора игрока: что ответил советник и что из этого получилось.
    """

    proposal_id: str = Field(..., min_length=1)
    option_id: str = Field(..., min_length=1)
    advisor_reply: str = Field(default="", description="Реплика советника после выбора")
    outcomes: list[AdvisorActionOutcome] = Field(default_factory=list)

    @property
    def executed_actions(self) -> list[AdvisorActionOutcome]:
        return [outcome for outcome in self.outcomes if outcome.is_executed]

    @property
    def has_unsupported_actions(self) -> bool:
        """
        Советник попросил навык, которого исполнитель пока не знает: повод
        показать игроку совет как непримененный.
        """
        return any(
            outcome.status == AdvisorActionStatus.NOT_SUPPORTED
            for outcome in self.outcomes
        )


# ====================================================
# Диалоговый режим
# ====================================================


class AdvisorAnswer(BaseModel):
    """
    Ответ советника на свободный вопрос игрока.
    """

    faction_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=_utc_now)


# ====================================================
# Ответы языковой модели
# ====================================================


class LLMAdvisorOption(BaseModel):
    """Вариант выбора глазами модели: только подпись и ее смысл."""

    label: str = Field(..., description="Подпись кнопки, например 'Поднять на 5%'")
    kind: AdvisorOptionKind = Field(
        default=AdvisorOptionKind.ACCEPT, description="Смысл кнопки"
    )


class LLMAdvisorProposalResponse(BaseModel):
    """
    Ожидаемый JSON-ответ советника при плановом осмотре державы.

    should_speak - право промолчать: в спокойный такт советник не обязан
    выдумывать повод для окна.
    """

    should_speak: bool = Field(
        ..., description="Есть ли повод беспокоить правителя в этот такт"
    )
    title: str = Field(default="Доклад советника", description="Заголовок окна")
    message: str = Field(default="", description="Что советник говорит правителю")
    options: list[LLMAdvisorOption] = Field(
        default_factory=list, description="Варианты ответа для правителя"
    )
