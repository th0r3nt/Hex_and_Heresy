"""
Инструменты советника державы.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.llm.models.skills import ToolDefinition


class ProposeAdvisorActionParams(BaseModel):
    """Параметры управленческого предложения советника правителю."""

    title: str = Field(..., min_length=1, description="Заголовок окна предложения")
    message: str = Field(
        ..., min_length=1, description="Развернутый текст рекомендации правителю"
    )
    options: list[str] = Field(
        ...,
        min_length=1,
        description="Варианты выбора для правителя (напр. 'Принять', 'Поднять на 5%')",
    )
    action_tool_name: Optional[str] = Field(
        default=None, description="Имя инструмента, предлагаемого к выполнению при согласии"
    )
    action_arguments: dict[str, Any] = Field(
        default_factory=dict, description="Аргументы для предлагаемого инструмента"
    )


PROPOSE_ADVISOR_ACTION = ToolDefinition(
    name="propose_advisor_action",
    description="Сформировать инициативное предложение правителю с вариантами решений и кнопками выбора.",
    parameters_model=ProposeAdvisorActionParams,
)
