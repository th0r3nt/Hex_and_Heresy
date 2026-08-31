"""
Контекст исполнения инструментов (Function Calling) языковой модели.
"""

from dataclasses import dataclass
from typing import Optional

from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.exceptions.llm import ToolContextMissingError
from src.back.l01_domain.world.models.state import WorldState


@dataclass
class ToolExecutionContext:
    """
    Контекст исполнения команд, переданных языковой моделью.
    Хранит ссылки на текущее состояние мира, активную фракцию и боевую обстановку.
    """

    world_state: WorldState
    caller_faction_id: Optional[str] = None
    battle_state: Optional[TacticalBattleState] = None
    actor_id: Optional[str] = None
    target_faction_id: Optional[str] = None

    # ====================================================
    # Валидаторы обязательных компонентов контекста
    # ====================================================

    def require_caller_faction_id(self, tool_name: str) -> str:
        """
        Возвращает идентификатор вызывающей фракции или выбрасывает ошибку.
        """
        if not self.caller_faction_id:
            raise ToolContextMissingError(
                tool_name=tool_name,
                missing_detail="идентификатор вызывающей фракции (caller_faction_id)",
            )
        return self.caller_faction_id

    def require_battle_state(self, tool_name: str) -> TacticalBattleState:
        """
        Возвращает активное состояние боя или выбрасывает ошибку.
        """
        if self.battle_state is None:
            raise ToolContextMissingError(
                tool_name=tool_name,
                missing_detail="активное состояние боя (battle_state)",
            )
        return self.battle_state

    def require_actor_id(self, tool_name: str) -> str:
        """
        Возвращает идентификатор конкретного актора (посла, командира) или ошибку.
        """
        if not self.actor_id:
            raise ToolContextMissingError(
                tool_name=tool_name,
                missing_detail="идентификатор актора (actor_id)",
            )
        return self.actor_id

    def require_target_faction_id(self, tool_name: str) -> str:
        """
        Возвращает идентификатор целевой фракции или выбрасывает ошибку.
        """
        if not self.target_faction_id:
            raise ToolContextMissingError(
                tool_name=tool_name,
                missing_detail="идентификатор целевой фракции (target_faction_id)",
            )
        return self.target_faction_id
