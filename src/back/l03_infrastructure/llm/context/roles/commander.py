from src.back.l01_domain.army.models.characters.commanders import Commander
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.models.state import WorldState

from src.back.l03_infrastructure.llm.context.blocks.military import build_army_block
from src.back.l03_infrastructure.llm.context.blocks.world import build_world_block


def build_commander_context(
    world_state: WorldState,
    commander: Commander,
    army: StrategicArmy,
) -> list[ContextBlock]:
    
    personal_lines = [
        f"Ты — полководец {commander.name}.",
        f"Твое воинское звание: {commander.role_title}.",
        f"Твои черты характера: {', '.join(t.name for t in commander.traits) if commander.traits else 'нет'}.",
        f"Боевой опыт: {commander.state.experience}.",
    ]

    if commander.custom_biography:
        personal_lines.append(f"Твоя предыстория: {commander.custom_biography}")

    if commander.personality_prompt_override:
        personal_lines.append(
            f"Особые черты характера: {commander.personality_prompt_override}"
        )

    blocks = [
        ContextBlock(
            title="Твое положение", body="\n".join(f"- {line}" for line in personal_lines)
        ),
        build_army_block(army),
        build_world_block(world_state),
    ]

    return blocks
