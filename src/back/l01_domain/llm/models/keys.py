"""
Безопасное представление ключа доступа к провайдеру языковых моделей.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.back.l01_domain.llm.constants import ApiKeyStatus


class ApiKeyView(BaseModel):
    """
    Безопасное представление ключа для экрана настроек.
    """

    model_config = ConfigDict(frozen=True)

    provider_id: str
    masked_value: str
    label: Optional[str] = None
    status: ApiKeyStatus
    failures: int = Field(default=0, ge=0)
