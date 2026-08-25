from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.models.state import WorldState

from src.back.l03_infrastructure.llm.context.blocks.diplomacy import build_diplomacy_block
from src.back.l03_infrastructure.llm.context.blocks.faction import build_faction_block
from src.back.l03_infrastructure.llm.context.blocks.world import build_world_block


def build_advisor_context(
    world_state: WorldState,
    faction: Faction,
) -> list[ContextBlock]:

    blocks = []

    blocks.append(
        ContextBlock(
            title="Твое положение",
            body="- Ты верный советник правителя. Ты находишься в ставке и анализируешь отчеты со всего мира.",
        )
    )

    # Советник видит всю макро-картину
    blocks.append(build_world_block(world_state))
    blocks.append(build_faction_block(faction))
    blocks.append(build_diplomacy_block(world_state, faction.id))

    return blocks
