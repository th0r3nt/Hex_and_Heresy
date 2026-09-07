"""
Базовые схемы, общие для всех роутеров.
"""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """
    Тело ответа при ошибке. Формируется в http/errors.py.
    """

    error: str = Field(..., description="Имя класса доменной ошибки")
    detail: str = Field(..., description="Человекочитаемое описание для интерфейса")


class OperationResult(BaseModel):
    """
    Ответ на команду, которой нечего вернуть кроме факта исполнения.
    """

    success: bool = Field(default=True)
    detail: str = Field(default="")
