"""
Модуль ротации API-ключей.

Обеспечивает высокую доступность вызовов LLM, автоматически переключая
ключи при достижении лимитов провайдера (HTTP 429) или удаляя невалидные (HTTP 401).
Использует стратегию Round-Robin для равномерного распределения нагрузки.
"""

import math
import time
from typing import List, Dict, Optional

from src.back.utils.logger import main_logger


class AllKeysExhaustedError(Exception):
    """Исключение, выбрасываемое, когда все доступные ключи находятся в кулдауне."""

    def __init__(self, wait_time: int) -> None:
        self.wait_time = wait_time
        super().__init__(f"Все ключи в кулдауне. Ожидание: {wait_time} сек.")


class APIKeyRotator:
    """
    Менеджер ключей для конкретного провайдера LLM.
    Отслеживает мертвые ключи и временные блокировки (Rate Limits).
    """

    def __init__(self, provider_id: str, keys: List[str]) -> None:
        self.provider_id = provider_id
        # Фильтруем пустые строки на случай кривых данных из конфига
        self.keys = [k.strip() for k in keys if k.strip()]

        # Хранит timestamp, до которого ключ недоступен из-за лимитов
        self._cooldowns: Dict[str, float] = {k: 0.0 for k in self.keys}
        self._current_index: int = 0

        if self.keys:
            main_logger.info(
                f"[LLM] Ротатор для '{self.provider_id}' инициализирован. Ключей: {len(self.keys)}."
            )
        else:
            main_logger.warning(
                f"[LLM] Ротатор для '{self.provider_id}' пуст (подходит только для локальных моделей)."
            )

    def get_next_key(self) -> Optional[str]:
        """
        Отдает следующий доступный ключ (Round-Robin), пропуская те, что в кулдауне.
        Возвращает None, если ключей нет в принципе.
        """
        if not self.keys:
            return None

        now = time.time()
        attempts = len(self.keys)

        # Ищем первый ключ, который не в кулдауне
        for _ in range(attempts):
            key = self.keys[self._current_index]
            self._current_index = (self._current_index + 1) % len(self.keys)

            if self._cooldowns.get(key, 0.0) <= now:
                return key

        # Если дошли сюда, значит все ключи заморожены.
        # Находим тот, который освободится раньше всех.
        soonest_key = min(self.keys, key=lambda k: self._cooldowns.get(k, 0.0))
        wait_time = max(1, math.ceil(self._cooldowns[soonest_key] - now))

        raise AllKeysExhaustedError(wait_time=wait_time)

    def ban_key(self, key: str) -> None:
        """
        Навсегда удаляет ключ из ротации (например, при HTTP 401).
        """
        if key in self.keys:
            self.keys.remove(key)
            self._cooldowns.pop(key, None)

            masked = key[:10] + "***" if len(key) > 10 else "***"
            main_logger.warning(
                f"[LLM] Ключ {masked} удален из пула '{self.provider_id}' (мертв)."
            )

            if self.keys:
                self._current_index = self._current_index % len(self.keys)

    def cooldown_key(self, key: str, seconds: int = 60) -> None:
        """
        Временно блокирует использование ключа (HTTP 429).
        """
        if key in self.keys:
            self._cooldowns[key] = time.time() + seconds
            masked = key[:8] + "***" if len(key) > 8 else "***"

            reason = "исчерпана квота" if seconds > 3600 else "лимит запросов"
            main_logger.warning(
                f"[LLM] Ключ {masked} ({self.provider_id}) заморожен на {seconds} сек. ({reason})."
            )

    def total_keys(self) -> int:
        """Считает оставшиеся живые ключи."""
        return len(self.keys)
