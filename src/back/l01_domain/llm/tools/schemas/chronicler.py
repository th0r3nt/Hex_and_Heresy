"""
Схемы параметров инструментов внутриигрового летописца.
"""

from pydantic import BaseModel, Field


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
