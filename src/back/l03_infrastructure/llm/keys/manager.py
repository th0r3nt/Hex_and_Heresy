"""
Менеджмент ключей для LLM. Отвечает за хранение и ротацию ключей.

Ключи вводит сам игрок в настройках игры, поэтому менеджер держит их только в
памяти процесса и наружу отдает исключительно маскированные представления.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Optional, Protocol, runtime_checkable

from src.back.l01_domain.exceptions import LLMKeyMissingError
from src.back.l01_domain.llm.constants import ApiKeyStatus
from src.back.l01_domain.llm.models.keys import ApiKeyView
from src.back.utils.logger import main_logger

# Сколько ключ отдыхает после отказа по квоте, прежде чем его снова попробуют
DEFAULT_COOLDOWN_SECONDS = 300


def mask_key(value: str) -> str:
    """
    Готовит ключ к показу в интерфейсе и логах: 'sk-proj-1234...cd90'.
    Полное значение ключа не должно попадать ни в лог, ни на фронт.
    """
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


class _ApiKeyRecord:
    """
    Внутренняя запись пула: сам секрет плюс его текущее здоровье.
    """

    def __init__(self, provider_id: str, value: str, label: Optional[str] = None) -> None:
        self.provider_id = provider_id
        self.value = value
        self.label = label
        self.status = ApiKeyStatus.ACTIVE
        self.failures = 0
        self.cooldown_until: Optional[datetime] = None

    def is_available(self, now: datetime) -> bool:
        if self.status is ApiKeyStatus.REVOKED:
            return False
        if self.status is ApiKeyStatus.COOLING_DOWN:
            return self.cooldown_until is None or now >= self.cooldown_until
        return True

    def to_view(self) -> ApiKeyView:
        return ApiKeyView(
            provider_id=self.provider_id,
            masked_value=mask_key(self.value),
            label=self.label,
            status=self.status,
            failures=self.failures,
        )


@runtime_checkable
class KeyRotationStrategy(Protocol):
    """
    Контракт выбора очередного ключа из доступных.
    """

    def select(self, provider_id: str, available: list[_ApiKeyRecord]) -> _ApiKeyRecord:
        ...


class RoundRobinRotation(KeyRotationStrategy):
    """
    Циклический перебор: размазывает нагрузку по всем ключам провайдера.
    Уместен, когда игрок вбил несколько бесплатных ключей с мелкими квотами.
    """

    def __init__(self) -> None:
        self._cursors: dict[str, int] = {}

    def select(self, provider_id: str, available: list[_ApiKeyRecord]) -> _ApiKeyRecord:
        cursor = self._cursors.get(provider_id, 0)
        record = available[cursor % len(available)]
        self._cursors[provider_id] = (cursor + 1) % len(available)
        return record


class PrimaryFirstRotation(KeyRotationStrategy):
    """
    Всегда первый живой ключ по порядку добавления.
    Уместен, когда первый ключ платный и качественный, а остальные - запасные.
    """

    def select(self, provider_id: str, available: list[_ApiKeyRecord]) -> _ApiKeyRecord:
        return available[0]


class ApiKeyManager:
    """
    Пул API-ключей по провайдерам: хранение, выдача и ротация.

    Здоровьем ключей управляет вызывающий клиент: он единственный видит ответ
    провайдера и сообщает сюда, приняли ключ или отвергли.
    """

    def __init__(
        self,
        rotation: Optional[KeyRotationStrategy] = None,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._pools: dict[str, list[_ApiKeyRecord]] = {}
        self._rotation = rotation or RoundRobinRotation()
        self._cooldown = timedelta(seconds=cooldown_seconds)
        self._clock = clock

    # ==================================================================
    # НАПОЛНЕНИЕ ПУЛА
    # ==================================================================

    def add_key(self, provider_id: str, value: str, label: Optional[str] = None) -> bool:
        """
        Добавляет ключ в пул провайдера. Пустые значения и дубликаты игнорируются.
        Возвращает True, если ключ действительно добавлен.
        """
        secret = value.strip()
        if not secret:
            return False

        pool = self._pools.setdefault(provider_id, [])
        if any(record.value == secret for record in pool):
            return False

        pool.append(_ApiKeyRecord(provider_id=provider_id, value=secret, label=label))
        main_logger.info(
            f"[LLM] Провайдеру '{provider_id}' добавлен ключ {mask_key(secret)}."
        )
        return True

    def set_keys(self, provider_id: str, values: Iterable[str]) -> int:
        """
        Полностью заменяет пул провайдера (сохранение экрана настроек).
        Возвращает количество принятых ключей.
        """
        self._pools.pop(provider_id, None)
        return sum(1 for value in values if self.add_key(provider_id, value))

    def load_from_env(self, provider_id: str, env_var: str) -> bool:
        """
        Подхватывает ключ из переменной окружения - запасной путь для разработки
        и запуска без экрана настроек.
        """
        return self.add_key(provider_id, os.getenv(env_var, ""), label=env_var)

    def remove_key(self, provider_id: str, masked_value: str) -> bool:
        """
        Удаляет ключ по его маскированному виду: настоящий секрет наружу не
        уходил, и вернуться от интерфейса он может только в таком виде.
        """
        pool = self._pools.get(provider_id, [])
        for i, record in enumerate(pool):
            if mask_key(record.value) == masked_value:
                pool.pop(i)
                return True
        return False

    def clear(self, provider_id: Optional[str] = None) -> None:
        """
        Очищает пул одного провайдера или все пулы сразу.
        """
        if provider_id is None:
            self._pools.clear()
        else:
            self._pools.pop(provider_id, None)

    # ==================================================================
    # ВЫДАЧА
    # ==================================================================

    def has_keys(self, provider_id: str) -> bool:
        """
        Есть ли у провайдера хотя бы один пригодный к работе ключ.
        """
        return bool(self._available(provider_id))

    def get_key(self, provider_id: str) -> str:
        """
        Выдает очередной рабочий ключ согласно стратегии ротации.
        Бросает LLMKeyMissingError, если живых ключей не осталось.
        """
        available = self._available(provider_id)
        if not available:
            raise LLMKeyMissingError(provider_id)

        return self._rotation.select(provider_id, available).value

    def list_keys(self, provider_id: Optional[str] = None) -> list[ApiKeyView]:
        """
        Отдает маскированный список ключей для экрана настроек.
        """
        if provider_id is not None:
            return [record.to_view() for record in self._pools.get(provider_id, [])]
        return [record.to_view() for pool in self._pools.values() for record in pool]

    # ==================================================================
    # ОБРАТНАЯ СВЯЗЬ О ЗДОРОВЬЕ КЛЮЧА
    # ==================================================================

    def report_success(self, provider_id: str, key: str) -> None:
        """
        Отмечает удачный запрос: ключ снова считается здоровым.
        """
        record = self._find(provider_id, key)
        if record is None:
            return
        record.status = ApiKeyStatus.ACTIVE
        record.failures = 0
        record.cooldown_until = None

    def report_rate_limited(self, provider_id: str, key: str) -> None:
        """
        Ключ уперся в квоту: отправляет его отдыхать, чтобы ротация ушла к следующему.
        """
        record = self._find(provider_id, key)
        if record is None:
            return
        record.status = ApiKeyStatus.COOLING_DOWN
        record.failures += 1
        record.cooldown_until = self._clock() + self._cooldown
        main_logger.warning(
            f"[LLM] Ключ {mask_key(key)} провайдера '{provider_id}' исчерпал квоту "
            f"и отдыхает до {record.cooldown_until.isoformat()}."
        )

    def report_rejected(self, provider_id: str, key: str) -> None:
        """
        Провайдер отверг ключ: сам он не починится, ждем вмешательства игрока.
        """
        record = self._find(provider_id, key)
        if record is None:
            return
        record.status = ApiKeyStatus.REVOKED
        record.failures += 1
        main_logger.error(
            f"[LLM] Ключ {mask_key(key)} провайдера '{provider_id}' отвергнут и отключен."
        )

    # ==================================================================
    # СЛУЖЕБНОЕ
    # ==================================================================

    def _available(self, provider_id: str) -> list[_ApiKeyRecord]:
        now = self._clock()
        return [record for record in self._pools.get(provider_id, []) if record.is_available(now)]

    def _find(self, provider_id: str, key: str) -> Optional[_ApiKeyRecord]:
        for record in self._pools.get(provider_id, []):
            if record.value == key:
                return record
        return None
