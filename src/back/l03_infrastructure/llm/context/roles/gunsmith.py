from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.models.state import WorldState

from src.back.l03_infrastructure.llm.context.blocks.faction import build_faction_block


def build_gunsmith_context(
    world_state: WorldState,
    faction: Faction,
) -> list[ContextBlock]:

    blocks = []

    personal_lines = [
        "Ты находишься в кузнях и мануфактурах своей фракции.",
        "Твоя задача — оценивать заказы лорда, чертить новые виды экипировки и следить за стоимостью их производства.",
    ]

    # Собираем список уже созданных чертежей
    custom_items = [eq for eq in world_state.custom_equipment.values() if eq.is_custom]
    if custom_items:
        items_str = ", ".join(f"'{eq.name}'" for eq in custom_items)
        personal_lines.append(f"Ты уже изобрел в этой партии: {items_str}.")
    else:
        personal_lines.append("Ты еще не создал ни одного уникального чертежа в этой партии.")

    blocks.append(
        ContextBlock(
            title="Твое положение", body="\n".join(f"- {line}" for line in personal_lines)
        )
    )

    blocks.append(build_faction_block(faction))

    return blocks
