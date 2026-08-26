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
    lord = lord_faction.lord

    personal_lines = [
        f"Твое имя: {lord.name}, титул: {lord.title}.",
        f"Твои черты: {', '.join(t.name for t in lord.traits) if lord.traits else 'нет'}.",
        f"Ты находишься в своей цитадели «{lord_faction.headquarters.name}».",
    ]

    if lord.custom_biography:
        personal_lines.append(f"Твоя предыстория: {lord.custom_biography}")

    if lord.personality_prompt_override:
        personal_lines.append(f"Особые черты характера: {lord.personality_prompt_override}")

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
            "Помни, что ты вправе приказать казнить его за дерзость, но это будет означать немедленную войну.",
        ]
        blocks.append(
            ContextBlock(
                title="Обстановка в тронном зале",
                body="\n".join(f"- {line}" for line in ambassador_lines),
            )
        )

    return blocks
