from typing import Optional

from src.back.l01_domain.army.models.characters.heroes import Hero
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.models.state import WorldState

from src.back.l03_infrastructure.llm.context.blocks.military import build_battle_block


def build_hero_context(
    world_state: WorldState,
    hero: Hero,
    battle_state: Optional[TacticalBattleState] = None,
) -> list[ContextBlock]:

    blocks = []

    personal_lines = [
        f"Ты — герой {hero.name}.",
        f"Твой архетип: {hero.archetype.name}. {hero.archetype.special_rule}",
        f"Текущее здоровье: {hero.state.current_hp:.1f} из {hero.max_hp:.1f}.",
    ]

    if hero.chosen_perks:
        perks = ", ".join(p.name for p in hero.chosen_perks)
        personal_lines.append(f"Изученные навыки: {perks}.")

    if hero.state.scars:
        scars_info = ", ".join(f"{s.name} ({s.description})" for s in hero.state.scars)
        personal_lines.append(f"Твои увечья и шрамы: {scars_info}.")

    blocks.append(
        ContextBlock(
            title="Твое положение", body="\n".join(f"- {line}" for line in personal_lines)
        )
    )

    if battle_state:
        blocks.append(build_battle_block(battle_state))

    return blocks
