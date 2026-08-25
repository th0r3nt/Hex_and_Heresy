"""
Фасад инфраструктуры LLM.

Единая точка входа для всех сервисов игры, реализующая `LLMClientProtocol`.
Оркестрирует конфигурациями провайдеров, ротаторами ключей и исполнителями (executors).
Поддерживает бесшовный фоллбэк: если основной провайдер (например, облако)
упал или исчерпал лимиты, запрос автоматически уходит локальной модели.
"""

from typing import Awaitable, Callable, Dict, List, Optional, TypeVar

from pydantic import BaseModel

from src.back.utils.logger import main_logger
from src.back.l01_domain.exceptions.llm import (
    LLMError,
    LLMKeyMissingError,
    LLMProviderNotConfiguredError,
)
from src.back.l01_domain.llm.models.provider import LLMProviderConfig
from src.back.l01_domain.protocols.llm import LLMClientProtocol

from src.back.l03_infrastructure.llm.keys.rotator import APIKeyRotator
from src.back.l03_infrastructure.llm.client import LLMClient
from src.back.l03_infrastructure.llm.executor import LLMExecutor

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")


class LLMFacade(LLMClientProtocol):
    """
    Управляет жизненным циклом компонентов LLM (ключи, клиенты, исполнители).
    """

    def __init__(self) -> None:
        self._providers: Dict[str, LLMProviderConfig] = {}

        # Инстансы рабочих компонентов
        self._rotators: Dict[str, APIKeyRotator] = {}
        self._clients: Dict[str, LLMClient] = {}
        self._executors: Dict[str, LLMExecutor] = {}

        self._active_id: Optional[str] = None
        self._fallback_ids: List[str] = []

    # ==================================================================
    # УПРАВЛЕНИЕ ПРОВАЙДЕРАМИ И КЛЮЧАМИ
    # ==================================================================

    def register_provider(self, config: LLMProviderConfig, make_active: bool = False) -> None:
        """Регистрирует настройки провайдера."""
        self._providers[config.id] = config

        # Если конфиг обновился, удаляем старые инстансы, чтобы они пересобрались
        self._clients.pop(config.id, None)
        self._executors.pop(config.id, None)

        if make_active or self._active_id is None:
            self._active_id = config.id

        main_logger.info(
            f"[LLM] Зарегистрирован провайдер '{config.id}' (модель '{config.model}')."
        )

    def set_api_keys(self, provider_id: str, keys: List[str]) -> None:
        """Инициализирует или обновляет ротатор ключей для провайдера."""
        config = self._providers.get(provider_id)
        if not keys and (config is None or config.requires_api_key):
            main_logger.warning(
                f"[LLM] Попытка передать пустой список ключей для '{provider_id}'."
            )

        self._rotators[provider_id] = APIKeyRotator(provider_id=provider_id, keys=keys)
        # Клиент и экзекутор должны быть пересобраны с новым ротатором
        self._clients.pop(provider_id, None)
        self._executors.pop(provider_id, None)

    def set_active_provider(self, provider_id: str) -> None:
        if provider_id not in self._providers:
            raise LLMProviderNotConfiguredError(provider_id)
        self._active_id = provider_id

    def set_fallback_chain(self, provider_ids: List[str]) -> None:
        for provider_id in provider_ids:
            if provider_id not in self._providers:
                raise LLMProviderNotConfiguredError(provider_id)
        self._fallback_ids = list(provider_ids)

    # ==================================================================
    # РЕАЛИЗАЦИЯ LLMClientProtocol
    # ==================================================================

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Маршрутизирует генерацию текста по цепочке провайдеров."""

        async def call(executor: LLMExecutor) -> str:
            return await executor.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        return await self._execute_with_fallbacks(call)

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        temperature: float = 0.6,
    ) -> T:
        """Маршрутизирует генерацию структурированного JSON по цепочке провайдеров."""

        async def call(executor: LLMExecutor) -> T:
            return await executor.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=response_model,
                temperature=temperature,
            )

        return await self._execute_with_fallbacks(call)

    async def close_all(self) -> None:
        """Очистка ресурсов (вызывается при graceful shutdown сервера)."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
        self._executors.clear()

    # ==================================================================
    # ВНУТРЕННЯЯ ЛОГИКА И СБОРКА
    # ==================================================================

    async def _execute_with_fallbacks(self, call: Callable[[LLMExecutor], Awaitable[R]]) -> R:
        """
        Прогоняет запрос через активного провайдера.
        При сбое передает запрос следующему запасному провайдеру в цепочке.
        """
        chain = self._resolve_chain()
        if not chain:
            raise LLMProviderNotConfiguredError()

        last_error: Optional[LLMError] = None

        for config in chain:
            if config.requires_api_key and self._rotators.get(config.id, None) is None:
                last_error = last_error or LLMKeyMissingError(config.id)
                continue

            executor = self._get_or_create_executor(config.id)

            try:
                return await call(executor)
            except LLMError as e:
                last_error = e
                main_logger.warning(
                    f"[LLM] Провайдер '{config.id}' не справился. Переход к запасному... Ошибка: {e.message}"
                )

        raise last_error or LLMProviderNotConfiguredError()

    def _resolve_chain(self) -> List[LLMProviderConfig]:
        """
        Возвращает цепочку провайдеров (основной + фоллбэки без дубликатов).
        """
        
        ordered_ids = []
        if self._active_id:
            ordered_ids.append(self._active_id)
        ordered_ids.extend(self._fallback_ids)

        chain = []
        seen = set()
        for pid in ordered_ids:
            if pid not in seen and pid in self._providers:
                chain.append(self._providers[pid])
                seen.add(pid)
        return chain

    def _get_or_create_executor(self, provider_id: str) -> LLMExecutor:
        """
        Ленивая сборка Клиента и Экзекутора для провайдера.
        """

        if provider_id in self._executors:
            return self._executors[provider_id]

        config = self._providers[provider_id]

        # Если ротатор не инициализирован (например для локальной модели без ключа), создаем пустой
        if provider_id not in self._rotators:
            self._rotators[provider_id] = APIKeyRotator(provider_id=provider_id, keys=[])

        rotator = self._rotators[provider_id]

        client = LLMClient(provider_id=provider_id, api_url=config.base_url, rotator=rotator)
        self._clients[provider_id] = client

        executor = LLMExecutor(config=config, client=client)
        self._executors[provider_id] = executor

        return executor
