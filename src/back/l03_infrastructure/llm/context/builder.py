"""
Сборка изменчивого контекста для LLM.

Промпт (prompt/) описывает, КЕМ является персонаж - это статика, склеенная из
markdown-блоков. Контекст описывает, ЧТО вокруг него происходит прямо сейчас:
ход, ресурсы, состояние армий, дипломатия. Он пересобирается на каждый запрос.

# TODO: методы - заглушки. Наполнять по мере готовности механик, каждая
# отдает свой блок; порядок и лимит блоков задает вызывающий сервис.
"""

from typing import Optional

from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.models.state import WorldState


class ContextBuilder:
    """
    Собирает блоки изменчивого контекста из состояния мира.

    Каждый блок независим: сервис механики берет только то, что нужно его
    персонажу. Лорду не нужна тактическая обстановка, командиру отряда -
    дипломатические отношения третьих фракций.
    """

    def build_world_context(self, world_state: WorldState) -> ContextBlock:
        """
        Общая обстановка: ход, время суток, активные глобальные события.
        """
        # TODO: заглушка
        return ContextBlock(title="Обстановка в мире")

    def build_faction_context(self, faction: Faction) -> ContextBlock:
        """
        Положение фракции: раса, ресурсы, зоны под контролем, постройки.
        """
        # TODO: заглушка
        return ContextBlock(title="Положение фракции")

    def build_army_context(self, army: StrategicArmy) -> ContextBlock:
        """
        Состояние армии: отряды, потери, боевой дух, полководец и герои.
        """
        # TODO: заглушка
        return ContextBlock(title="Состояние армии")

    def build_diplomacy_context(
        self, world_state: WorldState, faction_id: str, counterpart_id: Optional[str] = None
    ) -> ContextBlock:
        """
        Дипломатия: отношения, пакты, войны, депеши и послы в пути.
        """
        # TODO: заглушка
        return ContextBlock(title="Дипломатическая обстановка")

    def build_battle_context(self, battle_state: TacticalBattleState) -> ContextBlock:
        """
        Тактическая обстановка: фаза боя, расстановка, потери сторон.
        Нужна летописцу для пересказа сражения и командирам - для реплик в бою.
        """
        # TODO: заглушка
        return ContextBlock(title="Обстановка боя")

    def render(self, blocks: list[ContextBlock]) -> str:
        """
        Склеивает непустые блоки в текстовую секцию контекста для промпта.
        """
        filled = [block for block in blocks if not block.is_empty]
        return "\n\n".join(f"## {block.title}\n{block.body.strip()}" for block in filled)
