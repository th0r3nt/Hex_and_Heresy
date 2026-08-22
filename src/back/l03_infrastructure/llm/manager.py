"""
Фасад. Принимает запросы от остальных модулей в коде и инкапсулирует сложность операций.

1. Принимает контекст;
2. Собирает промпт;
3. Находит подходящие навыки из Function Calling;
4. Берет подходящий ключ;
5. Вызывает LLM;
6. Получает JSON-ответ.

Сейчас закрыты шаги 4-6: выбор провайдера, ключ, вызов и разбор ответа.
Сборка промпта и навыки приедут вместе с prompt/builder.py и остаются за
пределами фасада: он принимает уже готовые system/user промпты.
"""

from typing import Awaitable, Callable, Optional, TypeVar

from pydantic import BaseModel

from src.back.l01_domain.exceptions import (
    LLMError,
    LLMKeyMissingError,
    LLMProviderNotConfiguredError,
)
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l03_infrastructure.llm.client import (
    LLMProviderConfig,
    LLMSessionFactoryProtocol,
    OpenAICompatibleClient,
)
from src.back.l03_infrastructure.llm.keys.manager import ApiKeyManager, ApiKeyView
from src.back.utils.logger import main_logger

T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")

# Как собрать клиента по конфигу провайдера: подменяется в тестах и при смене транспорта
LLMClientFactory = Callable[[LLMProviderConfig, ApiKeyManager], LLMClientProtocol]


def _default_client_factory(
    config: LLMProviderConfig, keys: ApiKeyManager
) -> LLMClientProtocol:
    return OpenAICompatibleClient(config=config, key_manager=keys)


class LLMManager(LLMClientProtocol):
    """
    Фасад управления языковыми моделями.

    Сам реализует LLMClientProtocol, поэтому сервисы механик зависят от
    доменного контракта, а не от реестра провайдеров: для летописца или
    дипломатии менеджер неотличим от одиночного клиента.

    Держит цепочку запасных провайдеров: если облако недоступно или ключ
    исчерпан, запрос уходит следующему в списке (например, локальной модели).
    """

    def __init__(
        self,
        key_manager: Optional[ApiKeyManager] = None,
        client_factory: LLMClientFactory = _default_client_factory,
        session_factory: Optional[LLMSessionFactoryProtocol] = None,
    ) -> None:
        self._keys = key_manager or ApiKeyManager()
        self._client_factory = client_factory
        self._session_factory = session_factory

        self._providers: dict[str, LLMProviderConfig] = {}
        self._clients: dict[str, LLMClientProtocol] = {}
        self._active_id: Optional[str] = None
        self._fallback_ids: list[str] = []

    # ==================================================================
    # РЕЕСТР ПРОВАЙДЕРОВ
    # ==================================================================

    def register_provider(self, config: LLMProviderConfig, make_active: bool = False) -> None:
        """
        Регистрирует провайдера. Первый зарегистрированный становится активным.
        """
        self._providers[config.id] = config
        self._clients.pop(config.id, None)  # конфиг мог измениться - клиента пересоберем

        if make_active or self._active_id is None:
            self._active_id = config.id

        main_logger.info(
            f"[LLM] Зарегистрирован провайдер '{config.id}' (модель '{config.model}')."
        )

    def remove_provider(self, provider_id: str) -> None:
        """
        Убирает провайдера из реестра вместе с его клиентом и местом в цепочке.
        """
        self._providers.pop(provider_id, None)
        self._clients.pop(provider_id, None)
        self._fallback_ids = [pid for pid in self._fallback_ids if pid != provider_id]

        if self._active_id == provider_id:
            self._active_id = next(iter(self._providers), None)

    def list_providers(self) -> list[LLMProviderConfig]:
        """
        Список зарегистрированных провайдеров для экрана настроек.
        """
        return list(self._providers.values())

    def set_active_provider(self, provider_id: str) -> None:
        """
        Выбирает провайдера по умолчанию.
        """
        if provider_id not in self._providers:
            raise LLMProviderNotConfiguredError(provider_id)
        self._active_id = provider_id

    def set_fallback_chain(self, provider_ids: list[str]) -> None:
        """
        Задает порядок запасных провайдеров на случай отказа активного.
        """
        for provider_id in provider_ids:
            if provider_id not in self._providers:
                raise LLMProviderNotConfiguredError(provider_id)
        self._fallback_ids = list(provider_ids)

    @property
    def active_provider(self) -> Optional[LLMProviderConfig]:
        """
        Текущий провайдер по умолчанию.
        """
        return self._providers.get(self._active_id) if self._active_id else None

    def is_ready(self) -> bool:
        """
        Готов ли хоть один провайдер обслужить запрос: зарегистрирован и,
        если требует ключ, ключ у него есть.
        """
        return any(self._is_usable(config) for config in self._resolve_chain())

    # ==================================================================
    # КЛЮЧИ (проксирование в экран настроек)
    # ==================================================================

    def add_api_key(self, provider_id: str, value: str, label: Optional[str] = None) -> bool:
        """
        Добавляет игроку ключ для провайдера.
        """
        return self._keys.add_key(provider_id, value, label=label)

    def set_api_keys(self, provider_id: str, values: list[str]) -> int:
        """
        Полностью заменяет набор ключей провайдера.
        """
        return self._keys.set_keys(provider_id, values)

    def list_api_keys(self, provider_id: Optional[str] = None) -> list[ApiKeyView]:
        """
        Маскированный список ключей для интерфейса.
        """
        return self._keys.list_keys(provider_id)

    # ==================================================================
    # ГЕНЕРАЦИЯ
    # ==================================================================

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Генерация свободного текста с проходом по цепочке провайдеров.
        """

        async def call(client: LLMClientProtocol) -> str:
            return await client.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        return await self._execute(call)

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        temperature: float = 0.6,
    ) -> T:
        """
        Генерация валидированного JSON с проходом по цепочке провайдеров.
        """

        async def call(client: LLMClientProtocol) -> T:
            return await client.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=response_model,
                temperature=temperature,
            )

        return await self._execute(call)

    # ==================================================================
    # СЛУЖЕБНОЕ
    # ==================================================================

    async def _execute(self, call: Callable[[LLMClientProtocol], Awaitable[R]]) -> R:
        """
        Прогоняет запрос по цепочке провайдеров до первого успеха.

        Отказ одного провайдера не должен ронять ход игры: партия может идти
        на локальной модели, пока облако лежит. Если не ответил никто -
        поднимается последняя ошибка.
        """
        chain = self._resolve_chain()
        if not chain:
            raise LLMProviderNotConfiguredError()

        last_error: Optional[LLMError] = None

        for config in chain:
            if not self._is_usable(config):
                last_error = last_error or LLMKeyMissingError(config.id)
                continue

            try:
                return await call(self._client_for(config))
            except LLMError as e:
                last_error = e
                main_logger.warning(
                    f"[LLM] Провайдер '{config.id}' не справился с запросом: {e.message}"
                )

        raise last_error or LLMProviderNotConfiguredError()

    def _resolve_chain(self) -> list[LLMProviderConfig]:
        """
        Активный провайдер, за ним запасные - без повторов и пропавших записей.
        """
        ordered_ids = [self._active_id, *self._fallback_ids] if self._active_id else list(self._fallback_ids)

        chain: list[LLMProviderConfig] = []
        seen: set[str] = set()
        for provider_id in ordered_ids:
            if provider_id is None or provider_id in seen:
                continue
            config = self._providers.get(provider_id)
            if config is not None:
                chain.append(config)
                seen.add(provider_id)
        return chain

    def _is_usable(self, config: LLMProviderConfig) -> bool:
        return not config.requires_api_key or self._keys.has_keys(config.id)

    def _client_for(self, config: LLMProviderConfig) -> LLMClientProtocol:
        """
        Отдает клиента провайдера, создавая его при первом обращении.
        Клиент дешев и без состояния соединения - сессия открывается на запрос.
        """
        client = self._clients.get(config.id)
        if client is None:
            client = self._build_client(config)
            self._clients[config.id] = client
        return client

    def _build_client(self, config: LLMProviderConfig) -> LLMClientProtocol:
        if self._session_factory is not None:
            return OpenAICompatibleClient(
                config=config, key_manager=self._keys, session_factory=self._session_factory
            )
        return self._client_factory(config, self._keys)
