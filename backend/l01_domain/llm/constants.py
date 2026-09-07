"""
Константы работы с большими языковыми моделями: роли диалога и состояния
ключей доступа.

Простые Enum, не несущие собственных данных.
"""

from enum import Enum


class ChatRole(str, Enum):
    """Роли участников диалога в формате Chat Completions."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ApiKeyStatus(str, Enum):
    """Состояние ключа в пуле провайдера."""

    ACTIVE = "active"  # Готов к работе
    COOLING_DOWN = "cooling_down"  # Уперся в лимит частоты или квоты, ждет
    REVOKED = "revoked"  # Провайдер отверг ключ: без вмешательства игрока бесполезен
