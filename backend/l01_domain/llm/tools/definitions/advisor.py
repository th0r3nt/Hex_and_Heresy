"""
Определения инструментов советника державы.
"""

from backend.l01_domain.llm.models.tools import ToolDefinition
from backend.l01_domain.llm.tools.schemas.advisor import ProposeAdvisorActionParams

PROPOSE_ADVISOR_ACTION = ToolDefinition(
    name="propose_advisor_action",
    description="Сформировать инициативное предложение правителю с вариантами решений и кнопками выбора.",
    parameters_model=ProposeAdvisorActionParams,
)
