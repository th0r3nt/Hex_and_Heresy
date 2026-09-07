"""
Настройки провайдера языковых моделей.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LLMProviderConfig(BaseModel):
    """
    Описание одного провайдера: куда стучаться, какой моделью и на каких условиях.
    Игрок задает это в настройках, поэтому конфиг - данные, а не код.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ..., min_length=1, description="Идентификатор провайдера (напр. 'openrouter')"
    )
    title: str = Field(..., min_length=1, description="Название для экрана настроек")
    model: str = Field(..., min_length=1, description="Имя модели у провайдера")

    base_url: Optional[str] = Field(
        default=None,
        description="Адрес OpenAI-совместимого эндпоинта; None - облако OpenAI",
    )
    requires_api_key: bool = Field(
        default=True, description="Локальные серверы обычно работают без ключа"
    )

    timeout_seconds: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=2, ge=0, description="Ретраи транспорта внутри SDK")

    supports_json_schema: bool = Field(
        default=True,
        description=(
            "Понимает ли провайдер response_format=json_schema. Если нет, схема "
            "уезжает текстом в системный промпт, а ответ просто просят в JSON"
        ),
    )
    strict_json_schema: bool = Field(
        default=False,
        description="Строгий режим схемы: поддерживают не все совместимые провайдеры",
    )
    structured_retries: int = Field(
        default=1,
        ge=0,
        description="Сколько раз переспросить модель, если она вернула невалидный JSON",
    )
