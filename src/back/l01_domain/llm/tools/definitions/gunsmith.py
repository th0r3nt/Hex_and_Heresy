"""
Определения инструментов оружейной мастерской.
"""

from src.back.l01_domain.llm.models.tools import ToolDefinition
from src.back.l01_domain.llm.tools.schemas.gunsmith import (
    DraftBlueprintParams,
    RejectBlueprintParams,
)

DRAFT_BLUEPRINT = ToolDefinition(
    name="draft_blueprint",
    description="Спроектировать чертеж нового предмета экипировки с расчетом характеристик и стоимости.",
    parameters_model=DraftBlueprintParams,
)

REJECT_BLUEPRINT = ToolDefinition(
    name="reject_blueprint",
    description="Отклонить запрос на создание предмета, если идея противоречит лору или культуре расы.",
    parameters_model=RejectBlueprintParams,
)
