"""
Фасад сборки изменчивого контекста для LLM.
Изолирует логику извлечения фактов из домена в текстовые блоки.
"""

from typing import Optional, Union

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.factions.models.diplomacy.messengers import Ambassador
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.models.battle_log import BattleDossier
from src.back.l01_domain.world.models.state import WorldState

# Прямые импорты из файлов ролей и блоков
from src.back.l03_infrastructure.llm.context.blocks.military import build_battle_summary_block
from src.back.l03_infrastructure.llm.context.roles.advisor import build_advisor_context
from src.back.l03_infrastructure.llm.context.roles.ambassador import build_ambassador_context
from src.back.l03_infrastructure.llm.context.roles.chronicler import (
    build_chronicle_context,
    build_rumor_context,
)
from src.back.l03_infrastructure.llm.context.roles.commander import build_commander_context
from src.back.l03_infrastructure.llm.context.roles.gunsmith import build_gunsmith_context
from src.back.l03_infrastructure.llm.context.roles.hero import build_hero_context
from src.back.l03_infrastructure.llm.context.roles.lord import build_lord_context
from src.back.l03_infrastructure.llm.context.roles.veteran import build_veteran_context


class ContextBuilder:
    """
    Предоставляет методы для генерации контекста под конкретных персонажей.
    """

    def build_lord_context(
        self,
        world_state: WorldState,
        lord_faction: Faction,
        counterpart_faction: Optional[Faction] = None,
        ambassador: Optional[Ambassador] = None,
    ) -> list[ContextBlock]:
        return build_lord_context(world_state, lord_faction, counterpart_faction, ambassador)

    def build_ambassador_context(
        self,
        world_state: WorldState,
        ambassador: Ambassador,
        envoy_faction: Faction,
        host_faction: Faction,
    ) -> list[ContextBlock]:
        return build_ambassador_context(world_state, ambassador, envoy_faction, host_faction)

    def build_commander_context(
        self,
        world_state: WorldState,
        commander: Commander,
        army: StrategicArmy,
    ) -> list[ContextBlock]:
        return build_commander_context(world_state, commander, army)

    def build_hero_context(
        self,
        world_state: WorldState,
        hero: Hero,
        battle_state: Optional[TacticalBattleState] = None,
    ) -> list[ContextBlock]:
        return build_hero_context(world_state, hero, battle_state)

    def build_veteran_context(
        self,
        world_state: WorldState,
        squad: Squad,
        battle_state: Optional[TacticalBattleState] = None,
    ) -> list[ContextBlock]:
        return build_veteran_context(world_state, squad, battle_state)

    def build_gunsmith_context(
        self,
        world_state: WorldState,
        faction: Faction,
    ) -> list[ContextBlock]:
        return build_gunsmith_context(world_state, faction)

    def build_advisor_context(
        self,
        world_state: WorldState,
        faction: Faction,
    ) -> list[ContextBlock]:
        return build_advisor_context(world_state, faction)

    def build_rumor_context(
        self,
        world_state: WorldState,
        faction: Optional[Faction] = None,
    ) -> list[ContextBlock]:
        return build_rumor_context(world_state, faction)

    def build_chronicle_context(
        self,
        dossier: BattleDossier,
        faction: Optional[Faction] = None,
    ) -> list[ContextBlock]:
        return build_chronicle_context(dossier, faction)

    def build_battle_summary_context(self, dossier: BattleDossier) -> ContextBlock:
        return build_battle_summary_block(dossier)

    def render(self, blocks: Union[list[ContextBlock], ContextBlock]) -> str:
        """
        Склеивает непустые блоки в текстовую секцию контекста для промпта.
        """
        if isinstance(blocks, ContextBlock):
            blocks = [blocks]

        filled = [block for block in blocks if not block.is_empty]
        return "\n\n".join(f"## {block.title}\n{block.body.strip()}" for block in filled)
