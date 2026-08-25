from typing import Optional

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.models.state import WorldState

from src.back.l03_infrastructure.llm.context.blocks.military import build_battle_block


def build_veteran_context(
    world_state: WorldState,
    squad: Squad,
    battle_state: Optional[TacticalBattleState] = None,
) -> list[ContextBlock]:

    blocks = []
    vet = squad.veterancy

    if vet.is_named:
        personal_lines = [
            f"Ты — {vet.commander_name}, командир именного отряда '{vet.squad_nickname}'.",
            f"В прошлом вы совершили подвиг: {vet.lore_description}",
            f"Ваша отличительная черта: {vet.trait_name}.",
        ]
    else:
        personal_lines = [f"Ты — командир безымянного отряда '{squad.archetype.name}'."]

    personal_lines.append(
        f"Текущее состояние отряда: осталось {squad.state.unit_count} бойцов, "
        f"мораль — {squad.state.morale:.1f}."
    )

    if squad.state.is_in_panic:
        personal_lines.append("Внимание: твой отряд сломлен и в панике отступает!")
    elif squad.state.is_exhausted:
        personal_lines.append("Внимание: твои бойцы физически истощены.")

    blocks.append(
        ContextBlock(
            title="Твое положение", body="\n".join(f"- {line}" for line in personal_lines)
        )
    )

    if battle_state:
        blocks.append(build_battle_block(battle_state))

    return blocks
