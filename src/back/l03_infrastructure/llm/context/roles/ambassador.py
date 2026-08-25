from src.back.l01_domain.factions.models.diplomacy.messengers import Ambassador
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.models.state import WorldState

from src.back.l03_infrastructure.llm.context.blocks.diplomacy import build_diplomacy_block


def build_ambassador_context(
    world_state: WorldState,
    ambassador: Ambassador,
    envoy_faction: Faction,
    host_faction: Faction,
) -> list[ContextBlock]:

    blocks = []

    traits = ", ".join(ambassador.traits) if ambassador.traits else "обычные"
    directive = ambassador.directive or "Добиться мира на любых разумных условиях."

    personal_lines = [
        f"Ты — {ambassador.name}, посол фракции '{envoy_faction.name}'.",
        f"Твои черты: {traits}.",
        f"Директива твоего лорда: {directive}",
        f"Прямо сейчас ты стоишь в цитадели фракции '{host_faction.name}' перед ее правителем.",
        "Помни: ты уязвим. Если лорд разгневается, тебя казнят прямо в тронном зале.",
    ]

    blocks.append(
        ContextBlock(
            title="Твое положение", body="\n".join(f"- {line}" for line in personal_lines)
        )
    )

    blocks.append(build_diplomacy_block(world_state, envoy_faction.id, host_faction.id))

    return blocks
