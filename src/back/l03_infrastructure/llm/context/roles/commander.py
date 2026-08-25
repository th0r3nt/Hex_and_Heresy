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

    blocks = []

    personal_lines = [
        f"Ты — полководец {commander.name}.",
        f"Твой архетип: {commander.archetype.name}. {commander.archetype.description}",
        f"Твоя черта: {commander.trait.name}. {commander.trait.text_fragment}",
        f"Боевой опыт: {commander.state.experience}.",
    ]

    blocks.append(
        ContextBlock(
            title="Твое положение", body="\n".join(f"- {line}" for line in personal_lines)
        )
    )

    blocks.append(build_army_block(army))
    blocks.append(build_world_block(world_state))

    return blocks
