"""
Протоколы работы с большими языковыми моделями (LLM).
"""

from typing import Any, Optional, Protocol, TypeVar, Union, runtime_checkable
from pydantic import BaseModel

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.factions.models.diplomacy.messengers import Ambassador
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.llm.models.tools import ToolCall, ToolDefinition
from src.back.l01_domain.world.models.battle_log import BattleDossier
from src.back.l01_domain.world.models.state import WorldState

T = TypeVar("T", bound=BaseModel)


# ====================================================
# Клиент модели
# ====================================================


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Контракт обращения к языковым моделям (локальным или облачным)."""

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Генерация свободного художественного текста (письма, летописи, слухи).
        """
        ...

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        temperature: float = 0.6,
    ) -> T:
        """
        Генерация строго валидированного JSON по Pydantic-модели через Structured Outputs.
        """
        ...

    async def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
        temperature: float = 0.6,
        tool_choice: Optional[Union[str, dict[str, Any]]] = "auto",
    ) -> tuple[str, list[ToolCall]]:
        """
        Генерация с передачей доступных инструментов (Function Calling).
        Возвращает текстовый ответ модели и список вызванных инструментов.
        """
        ...


# ====================================================
# Статические промпты
# ====================================================


@runtime_checkable
class PromptBuilderProtocol(Protocol):
    """
    Контракт сборки статического промпта из логических ключей каталога
    (см. l01_domain/llm/prompts.py).
    """

    def build(self, keys: list[str]) -> str:
        """Склеивает тексты по ключам в единый системный промпт."""
        ...


# ====================================================
# Изменчивый контекст
# ====================================================


@runtime_checkable
class ContextBuilderProtocol(Protocol):
    """
    Контракт сборки блоков изменчивого контекста под конкретные роли
    и их склейки в текстовую секцию промпта.
    """

    def build_lord_context(
        self,
        world_state: WorldState,
        lord_faction: Faction,
        counterpart_faction: Optional[Faction] = None,
        ambassador: Optional[Ambassador] = None,
    ) -> list[ContextBlock]: ...

    def build_ambassador_context(
        self,
        world_state: WorldState,
        ambassador: Ambassador,
        envoy_faction: Faction,
        host_faction: Faction,
    ) -> list[ContextBlock]: ...

    def build_commander_context(
        self,
        world_state: WorldState,
        commander: Commander,
        army: StrategicArmy,
    ) -> list[ContextBlock]: ...

    def build_hero_context(
        self,
        world_state: WorldState,
        hero: Hero,
        battle_state: Optional[TacticalBattleState] = None,
    ) -> list[ContextBlock]: ...

    def build_veteran_context(
        self,
        world_state: WorldState,
        squad: Squad,
        battle_state: Optional[TacticalBattleState] = None,
    ) -> list[ContextBlock]: ...

    def build_gunsmith_context(
        self,
        world_state: WorldState,
        faction: Faction,
    ) -> list[ContextBlock]: ...

    def build_advisor_context(
        self,
        world_state: WorldState,
        faction: Faction,
    ) -> list[ContextBlock]: ...

    def build_rumor_context(
        self,
        world_state: WorldState,
        faction: Optional[Faction] = None,
    ) -> list[ContextBlock]: ...

    def build_chronicle_context(
        self,
        dossier: BattleDossier,
        faction: Optional[Faction] = None,
    ) -> list[ContextBlock]: ...

    def build_battle_summary_context(self, dossier: BattleDossier) -> ContextBlock: ...

    def render(self, blocks: Union[list[ContextBlock], ContextBlock]) -> str:
        """Склеивает непустые блоки в текстовую секцию контекста для промпта."""
        ...
