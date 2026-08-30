"""
Исключения обращений к языковым моделям и вызова инструментов.
"""

from typing import Optional

from src.back.l01_domain.exceptions.base import DomainError


class LLMError(DomainError):
    """
    Базовое исключение для обращений к языковым моделям.
    """


class LLMProviderNotConfiguredError(LLMError):
    """
    Провайдер модели не зарегистрирован или не выбран в настройках игры.
    """

    def __init__(self, provider_id: Optional[str] = None) -> None:
        self.provider_id = provider_id
        target = (
            f"Провайдер LLM '{provider_id}' не зарегистрирован"
            if provider_id
            else "Активный провайдер LLM не выбран"
        )
        super().__init__(f"{target}: проверьте настройки языковых моделей.")


class LLMKeyMissingError(LLMError):
    """
    Для провайдера не задан ни один рабочий API-ключ.
    """

    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        super().__init__(
            f"Для провайдера '{provider_id}' нет доступных API-ключей: добавьте ключ в настройках."
        )


class LLMRequestFailedError(LLMError):
    """
    Запрос к языковой модели не выполнен (сеть, таймаут, ошибка сервера).
    """

    def __init__(self, provider_id: str, model: str, reason: str) -> None:
        self.provider_id = provider_id
        self.model = model
        self.reason = reason
        super().__init__(
            f"Запрос к модели '{model}' провайдера '{provider_id}' не выполнен: {reason}."
        )


class LLMAuthorizationError(LLMRequestFailedError):
    """
    Провайдер отверг API-ключ.
    """


class LLMRateLimitError(LLMRequestFailedError):
    """
    Провайдер исчерпал квоту или ограничил частоту запросов.
    """


class LLMResponseFormatError(LLMError):
    """
    Модель вернула ответ, не соответствующий ожидаемой JSON-схеме.
    """

    def __init__(self, model: str, reason: str) -> None:
        self.model = model
        self.reason = reason
        super().__init__(f"Модель '{model}' вернула невалидный структурный ответ: {reason}.")


class ToolError(LLMError):
    """
    Базовое исключение для ошибок инструментов и навыков.
    """


class ToolContextMissingError(ToolError):
    """
    Для выполнения инструмента в контексте не хватает обязательных данных.
    """

    def __init__(self, tool_name: str, missing_detail: str) -> None:
        self.tool_name = tool_name
        self.missing_detail = missing_detail
        super().__init__(
            f"Для выполнения инструмента '{tool_name}' не хватает контекста: {missing_detail}."
        )


class InvalidToolCallError(ToolError):
    """
    Вызов инструмента невалиден (неизвестное имя или некорректные аргументы).
    """

    def __init__(self, tool_name: str, reason: str) -> None:
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"Некорректный вызов инструмента '{tool_name}': {reason}.")
