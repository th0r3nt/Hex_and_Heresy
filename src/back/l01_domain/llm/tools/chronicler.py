"""
Инструменты внутриигрового летописца.
"""

from pydantic import BaseModel, Field

from src.back.l01_domain.llm.models.skills import ToolDefinition


class RecordChronicleParams(BaseModel):
    """Параметры создания художественной страницы летописи о бое."""

    title: str = Field(..., min_length=1, description="Заголовок страницы летописи")
    quote: str = Field(default="", description="Атмосферная цитата эпохи")
    body: str = Field(..., min_length=1, description="Художественный рассказ о ходе битвы")


class RecordEpitaphParams(BaseModel):
    """Параметры создания надгробия для Зала павших."""

    title: str = Field(..., min_length=1, description="Заголовок записи о погибших")
    epitaph: str = Field(
        ..., min_length=1, description="Текст эпитафии об их подвиге и гибели"
    )


class RecordFinaleParams(BaseModel):
    """Параметры финальной главы хроники партии."""

    title: str = Field(..., min_length=1, description="Заголовок финальной главы")
    body: str = Field(
        ..., min_length=1, description="Текст оды победителю или реквиема павшей державе"
    )


class SpeakRumorParams(BaseModel):
    """Параметры фонового слуха для окна логов."""

    text: str = Field(
        ..., min_length=1, description="Короткая атмосферная фраза о событиях в мире"
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
