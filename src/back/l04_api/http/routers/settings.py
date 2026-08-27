"""
Настройки языковых моделей: провайдеры, API-ключи, проверка связи.

Ключи движутся только внутрь: наружу отдается их количество, но не значения.
"""

from fastapi import APIRouter

from src.back.l04_api.dependencies import LLM
from src.back.l04_api.http.schemas.common import OperationResult
from src.back.l04_api.http.schemas.settings import (
    FallbackChainRequest,
    LLMSettingsResponse,
    PingResponse,
    ProviderKeysRequest,
    ProviderRegisterRequest,
    ProviderView,
)

router = APIRouter(prefix="/settings/llm", tags=["settings"])


# ====================================================
# Витрина настроек
# ====================================================


@router.get("", response_model=LLMSettingsResponse)
async def get_llm_settings(llm: LLM) -> LLMSettingsResponse:
    """Полная картина настроек моделей для экрана настроек."""
    active_id = llm.active_provider_id
    return LLMSettingsResponse(
        providers=[
            ProviderView.from_config(
                config,
                is_active=config.id == active_id,
                keys_count=llm.keys_count(config.id),
            )
            for config in llm.providers
        ],
        active_provider_id=active_id,
        fallback_chain=llm.fallback_chain,
    )


# ====================================================
# Провайдеры и ключи
# ====================================================


@router.post("/providers", response_model=OperationResult)
async def register_provider(
    payload: ProviderRegisterRequest, llm: LLM
) -> OperationResult:
    """Регистрирует или обновляет настройки провайдера."""
    llm.register_provider(payload.config, make_active=payload.make_active)
    return OperationResult(detail=f"Провайдер '{payload.config.id}' сохранен.")


@router.put("/providers/{provider_id}/keys", response_model=OperationResult)
async def set_provider_keys(
    provider_id: str, payload: ProviderKeysRequest, llm: LLM
) -> OperationResult:
    """Заменяет набор API-ключей провайдера."""
    llm.set_api_keys(provider_id, payload.keys)
    return OperationResult(detail=f"Ключей у провайдера '{provider_id}': {len(payload.keys)}.")


@router.post("/providers/{provider_id}/activate", response_model=OperationResult)
async def activate_provider(provider_id: str, llm: LLM) -> OperationResult:
    """Делает провайдера основным."""
    llm.set_active_provider(provider_id)
    return OperationResult(detail=f"Активный провайдер: '{provider_id}'.")


@router.put("/fallback-chain", response_model=OperationResult)
async def set_fallback_chain(payload: FallbackChainRequest, llm: LLM) -> OperationResult:
    """Задает порядок запасных провайдеров при отказе основного."""
    llm.set_fallback_chain(payload.provider_ids)
    return OperationResult(detail=f"Цепочка отката: {len(payload.provider_ids)} провайдеров.")


# ====================================================
# Проверка связи
# ====================================================


@router.post("/providers/{provider_id}/ping", response_model=PingResponse)
async def ping_provider(provider_id: str, llm: LLM) -> PingResponse:
    """
    Короткий запрос к модели.

    Отказ провайдера - это ответ на вопрос «живой ли он», поэтому приезжает
    обычным 200 с is_alive=false. Ошибкой считается только незаполненная
    настройка: нет такого провайдера или нет ключей.
    """
    return PingResponse(provider_id=provider_id, is_alive=await llm.ping(provider_id))
