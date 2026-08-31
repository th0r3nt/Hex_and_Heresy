"""
Диспетчер исполнения инструментов (Function Calling) языковой модели.
"""

from typing import Any, Awaitable, Callable, NamedTuple, Optional, Union

from src.back.l01_domain.exceptions.base import DomainError
from src.back.l01_domain.exceptions.llm import InvalidToolCallError
from src.back.l01_domain.llm.models.tools import ToolCall, ToolDefinition, ToolResult
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.utils.logger import main_logger

# Тип результата обработчика: готовый ToolResult, строка или кортеж (строка, данные)
HandlerRawOutput = Union[ToolResult, str, tuple[str, Optional[dict[str, Any]]]]
ToolHandlerFunc = Callable[[Any, ToolExecutionContext], Awaitable[HandlerRawOutput]]


class _RegisteredHandler(NamedTuple):
    definition: ToolDefinition
    handler: ToolHandlerFunc


class ToolExecutor:
    """
    Диспетчер вызовов инструментов.
    Оркестрирует сопоставление вызовов с зарегистрированными обработчиками,
    валидацию входных параметров и изоляцию доменных исключений.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, _RegisteredHandler] = {}

    # ====================================================
    # Регистрация обработчиков
    # ====================================================

    def register_handler(
        self,
        definition: ToolDefinition,
        handler: ToolHandlerFunc,
    ) -> None:
        """
        Регистрирует инструмент и его асинхронный обработчик.
        """
        self._handlers[definition.name] = _RegisteredHandler(
            definition=definition,
            handler=handler,
        )
        main_logger.debug(f"[ToolExecutor] Зарегистрирован инструмент: {definition.name}")

    def has_handler(self, tool_name: str) -> bool:
        """
        Проверяет, зарегистрирован ли обработчик для данного инструмента.
        """
        return tool_name in self._handlers

    def get_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """
        Возвращает определение инструмента по имени.
        """
        registered = self._handlers.get(tool_name)
        return registered.definition if registered is not None else None

    def list_definitions(self) -> list[ToolDefinition]:
        """
        Возвращает список всех зарегистрированных определений инструментов.
        """
        return [reg.definition for reg in self._handlers.values()]

    # ====================================================
    # Исполнение вызовов
    # ====================================================

    async def execute(
        self,
        tool_call: ToolCall,
        context: ToolExecutionContext,
    ) -> ToolResult:
        """
        Выполняет одиночный вызов инструмента с перехватом ошибок.
        """
        registered = self._handlers.get(tool_call.name)
        if registered is None:
            main_logger.warning(
                f"[ToolExecutor] Вызов неизвестного инструмента: '{tool_call.name}'"
            )
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=f"Инструмент '{tool_call.name}' не поддерживается системой.",
            )

        definition, handler = registered

        # 1. Валидация аргументов через Pydantic-схему
        try:
            params = tool_call.parse_arguments(definition.parameters_model)
        except InvalidToolCallError as error:
            main_logger.warning(
                f"[ToolExecutor] Невалидные аргументы для '{tool_call.name}': {error.message}"
            )
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=f"Некорректные параметры инструмента: {error.message}",
            )
        except Exception as error:
            main_logger.error(
                f"[ToolExecutor] Ошибка парсинга аргументов '{tool_call.name}': {error}"
            )
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=f"Ошибка парсинга параметров: {error}",
            )

        # 2. Выполнение обработчика с перехватом доменных и системных ошибок
        try:
            raw_result = await handler(params, context)
        except DomainError as error:
            main_logger.warning(
                f"[ToolExecutor] Доменная ошибка при вызове '{tool_call.name}': {error.message}"
            )
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=error.message,
            )
        except Exception as error:
            main_logger.error(
                f"[ToolExecutor] Непредвиденная ошибка при вызове '{tool_call.name}': {error}"
            )
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                success=False,
                error=f"Внутренняя ошибка при выполнении действия: {error}",
            )

        # 3. Нормализация результата
        return self._normalize_result(tool_call, raw_result)

    async def execute_many(
        self,
        tool_calls: list[ToolCall],
        context: ToolExecutionContext,
    ) -> list[ToolResult]:
        """
        Последовательно выполняет список вызовов инструментов.
        """
        results: list[ToolResult] = []
        for call in tool_calls:
            result = await self.execute(call, context)
            results.append(result)
        return results

    # ====================================================
    # Вспомогательные методы
    # ====================================================

    @staticmethod
    def _normalize_result(tool_call: ToolCall, raw_result: HandlerRawOutput) -> ToolResult:
        """
        Приводит вывод функции-обработчика к строгому объекту ToolResult.
        """
        if isinstance(raw_result, ToolResult):
            return raw_result

        if isinstance(raw_result, tuple):
            output_text, data_dict = raw_result
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                success=True,
                output=output_text,
                data=data_dict,
            )

        if isinstance(raw_result, str):
            return ToolResult(
                call_id=tool_call.id,
                tool_name=tool_call.name,
                success=True,
                output=raw_result,
            )

        return ToolResult(
            call_id=tool_call.id,
            tool_name=tool_call.name,
            success=True,
            output="Действие успешно выполнено.",
        )
