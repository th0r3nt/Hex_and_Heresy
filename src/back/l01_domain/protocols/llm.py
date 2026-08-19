"""
Протокол клиента больших языковых моделей (LLM).
"""

from typing import Optional, Protocol, TypeVar, runtime_checkable
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Контракт обращения к языковым моделям (локальным или облачным)."""

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Генерация свободного художественного текста (письма, летописи, слухи).
        """
        ...

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        temperature: float = 0.6,
    ) -> T:
        """
        Генерация строго валидированного JSON по Pydantic-модели через function calling.
        """
        ...
