"""
Определения инструментов советника державы.
"""

from src.back.l01_domain.llm.models.tools import ToolDefinition
from src.back.l01_domain.llm.tools.schemas.advisor import ProposeAdvisorActionParams

PROPOSE_ADVISOR_ACTION = ToolDefinition(
    name="propose_advisor_action",
    description="Сформировать инициативное предложение правителю с вариантами решений и кнопками выбора.",
    parameters_model=ProposeAdvisorActionParams,
)
