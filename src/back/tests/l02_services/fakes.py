"""
Доменные фейки сборщиков промптов и контекста для тестов сервисного слоя,
а также скриптованный клиент языковой модели с вызовами навыков.

Сервисы знают только протоколы из l01_domain, поэтому их тесты не поднимают
инфраструктуру: ни файлов промптов с диска, ни настоящего ContextBuilder.
Реальные реализации проверяются в tests/l03_infrastructure/llm/.
"""

import json
from typing import Any, NamedTuple, Union

from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.llm.models.tools import ToolCall


# ====================================================
# Статические промпты
# ====================================================


class FakePromptBuilder:
    """Вместо текста файлов отдает сами логические ключи каталога."""

    def build(self, keys: list[str]) -> str:
        return "\n\n".join(f"[{key}]" for key in keys)


# ====================================================
# Изменчивый контекст
# ====================================================


class FakeContextBuilder:
    """
    Отдает по одному опознаваемому блоку на роль: тестам сервисов важно, что
    контекст запрошен и доехал до промпта, а не как он собран из мира.
    """

    def _block(self, role: str) -> list[ContextBlock]:
        return [ContextBlock(title=f"Контекст: {role}", body=f"[{role}]")]

    def build_lord_context(
        self, world_state, lord_faction, counterpart_faction=None, ambassador=None
    ) -> list[ContextBlock]:
        return self._block("lord")

    def build_ambassador_context(
        self, world_state, ambassador, envoy_faction, host_faction
    ) -> list[ContextBlock]:
        return self._block("ambassador")

    def build_commander_context(self, world_state, commander, army) -> list[ContextBlock]:
        return self._block("commander")

    def build_hero_context(self, world_state, hero, battle_state=None) -> list[ContextBlock]:
        return self._block("hero")

    def build_veteran_context(
        self, world_state, squad, battle_state=None
    ) -> list[ContextBlock]:
        return self._block("veteran")

    def build_gunsmith_context(self, world_state, faction) -> list[ContextBlock]:
        return self._block("gunsmith")

    def build_advisor_context(self, world_state, faction) -> list[ContextBlock]:
        return self._block("advisor")

    def build_rumor_context(self, world_state, faction=None) -> list[ContextBlock]:
        return self._block("rumor")

    def build_chronicle_context(self, dossier, faction=None) -> list[ContextBlock]:
        return self._block("chronicle")

    def build_battle_summary_context(self, dossier) -> ContextBlock:
        return self._block("battle_summary")[0]

    def render(self, blocks: Union[list[ContextBlock], ContextBlock]) -> str:
        if isinstance(blocks, ContextBlock):
            blocks = [blocks]

        filled = [block for block in blocks if not block.is_empty]
        return "\n\n".join(f"## {block.title}\n{block.body.strip()}" for block in filled)


# ====================================================
# Готовая пара для конструкторов сервисов
# ====================================================


def fake_builders() -> tuple[FakePromptBuilder, FakeContextBuilder]:
    """Пара сборщиков для сервисов, которым нужны оба."""
    return FakePromptBuilder(), FakeContextBuilder()


# ====================================================
# Вызовы навыков
# ====================================================


def tool_call(tool_name: str, /, **arguments: Any) -> ToolCall:
    """
    Вызов навыка так, как его вернул бы провайдер: словарь аргументов
    вместе с исходной JSON-строкой.

    Имя навыка передается позиционно: среди аргументов самих навыков
    встречается и `name` (например, у чертежа оружейника).
    """
    return ToolCall(
        name=tool_name,
        arguments=arguments,
        raw_arguments=json.dumps(arguments, ensure_ascii=False),
    )


class LLMReply(NamedTuple):
    """
    Один ответ модели в режиме Function Calling: свободный текст и вызовы навыков.
    """

    content: str = ""
    calls: list[ToolCall] = []


def reply(content: str = "", *calls: ToolCall) -> LLMReply:
    """Короткая запись ответа модели для скрипта фейкового клиента."""
    return LLMReply(content=content, calls=list(calls))


__all__ = [
    "FakePromptBuilder",
    "FakeContextBuilder",
    "fake_builders",
    "tool_call",
    "LLMReply",
    "reply",
]
