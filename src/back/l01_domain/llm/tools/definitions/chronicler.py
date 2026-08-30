"""
Определения инструментов внутриигрового летописца.
"""

from src.back.l01_domain.llm.models.tools import ToolDefinition
from src.back.l01_domain.llm.tools.schemas.chronicler import (
    RecordChronicleParams,
    RecordEpitaphParams,
    RecordFinaleParams,
    SpeakRumorParams,
)

RECORD_CHRONICLE = ToolDefinition(
    name="record_chronicle",
    description="Записать страницу в историческую хронику сражений в культурном стиле фракции.",
    parameters_model=RecordChronicleParams,
)

RECORD_EPITAPH = ToolDefinition(
    name="record_epitaph",
    description="Составить надгробную эпитафию для Зала павших о погибшем именном отряде или герое.",
    parameters_model=RecordEpitaphParams,
)

RECORD_FINALE = ToolDefinition(
    name="record_finale",
    description="Написать заключительную главу летописи по итогам завершения кампании.",
    parameters_model=RecordFinaleParams,
)

SPEAK_RUMOR = ToolDefinition(
    name="speak_rumor",
    description="Сгенерировать короткий фоновый слух для окна игровых логов в период затишья.",
    parameters_model=SpeakRumorParams,
)
