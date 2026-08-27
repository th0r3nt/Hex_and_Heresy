"""
Схемы экрана настроек языковых моделей.

Ключи наружу не выдаются никогда: интерфейсу достаточно знать, сколько их
заведено у провайдера.
"""

from typing import Optional

from pydantic import BaseModel, Field

from src.back.l01_domain.llm.models.provider import LLMProviderConfig


class ProviderView(BaseModel):
    """
    Строка списка провайдеров на экране настроек.
    """

    id: str = Field(...)
    title: str = Field(...)
    model: str = Field(...)
    base_url: Optional[str] = Field(default=None)
    requires_api_key: bool = Field(default=True)

    is_active: bool = Field(default=False)
    keys_count: int = Field(default=0, ge=0, description="Число заведенных ключей")

    @classmethod
    def from_config(
        cls, config: LLMProviderConfig, is_active: bool, keys_count: int
    ) -> "ProviderView":
        return cls(
            id=config.id,
            title=config.title,
            model=config.model,
            base_url=config.base_url,
            requires_api_key=config.requires_api_key,
            is_active=is_active,
            keys_count=keys_count,
        )


class LLMSettingsResponse(BaseModel):
    """
    Полная картина настроек моделей.
    """

    providers: list[ProviderView] = Field(default_factory=list)
    active_provider_id: Optional[str] = Field(default=None)
    fallback_chain: list[str] = Field(default_factory=list)


class ProviderRegisterRequest(BaseModel):
    """
    Регистрация или обновление настроек провайдера.
    """

    config: LLMProviderConfig = Field(...)
    make_active: bool = Field(default=False)


class ProviderKeysRequest(BaseModel):
    """
    Замена набора API-ключей провайдера.
    """

    keys: list[str] = Field(default_factory=list)


class FallbackChainRequest(BaseModel):
    """
    Порядок запасных провайдеров при отказе основного.
    """

    provider_ids: list[str] = Field(default_factory=list)


class PingResponse(BaseModel):
    """
    Результат проверки связи с провайдером.
    """

    provider_id: str = Field(...)
    is_alive: bool = Field(...)
