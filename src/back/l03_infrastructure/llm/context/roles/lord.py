from typing import Optional

from src.back.l01_domain.factions.models.diplomacy.messengers import Ambassador
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.models.state import WorldState

from src.back.l03_infrastructure.llm.context.blocks.diplomacy import build_diplomacy_block
from src.back.l03_infrastructure.llm.context.blocks.faction import build_faction_block


def build_lord_context(
    world_state: WorldState,
    lord_faction: Faction,
    counterpart_faction: Optional[Faction] = None,
    ambassador: Optional[Ambassador] = None,
) -> list[ContextBlock]:
    """
    Контекст для правителя, принимающего дипломатическое решение.
    """
    lord = lord_faction.lord

    personal_lines = [
        f"Твое имя: {lord.name}, титул: {lord.title}.",
        f"Архетип: {lord.archetype.name} ({lord.archetype.description}).",
        f"Характер: {lord.trait.name} ({lord.trait.text_fragment}).",
        f"Ты находишься в своей цитадели «{lord_faction.headquarters.name}».",
    ]

    blocks = [
        ContextBlock(
            title="Твой личный статус", body="\n".join(f"- {line}" for line in personal_lines)
        ),
        build_faction_block(lord_faction),
        build_diplomacy_block(
            world_state,
            lord_faction.id,
            counterpart_faction.id if counterpart_faction is not None else None,
        ),
    ]

    if ambassador is not None:
        traits = (
            ", ".join(ambassador.traits)
            if ambassador.traits
            else "обычные, ничем не примечательные"
        )
        ambassador_lines = [
            f"Перед твоим троном стоит посол по имени {ambassador.name}.",
            f"Его характерные черты: {traits}.",
            "Помни, что ты вправе приказать казнить его за дерзость, но это будет означать немедленную войну, поэтому обдумывай свои решения.",
        ]
        blocks.append(
            ContextBlock(
                title="Обстановка в тронном зале",
                body="\n".join(f"- {line}" for line in ambassador_lines),
            )
        )

    return blocks
