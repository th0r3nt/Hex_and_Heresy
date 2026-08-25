from typing import Optional

from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.models.battle_log import BattleDossier
from src.back.l01_domain.world.models.state import WorldState

from src.back.l03_infrastructure.llm.context.blocks.diplomacy import build_world_wars_block
from src.back.l03_infrastructure.llm.context.blocks.faction import build_faction_block
from src.back.l03_infrastructure.llm.context.blocks.world import build_world_block


def build_rumor_context(
    world_state: WorldState,
    faction: Optional[Faction] = None,
) -> list[ContextBlock]:
    """
    Обстановка на карте для фонового слуха: летописец смотрит на мир целиком,
    поэтому войны берутся по всем парам, а не только по своей фракции.
    """
    blocks = []

    if faction is not None:
        blocks.append(
            ContextBlock(
                title="Твое положение",
                body=f"- Ты пишешь для фракции '{faction.name}' (раса: {faction.race.value}).",
            )
        )

    blocks.append(build_world_block(world_state))
    blocks.append(build_world_wars_block(world_state))

    if faction is not None:
        blocks.append(build_faction_block(faction))

    return blocks


def build_chronicle_context(
    dossier: BattleDossier,
    faction: Optional[Faction] = None,
) -> list[ContextBlock]:
    """
    Чем это сражение особенное для пера: чью сторону летописец держит и что
    из боя запомнят. Числа боя идут отдельно, готовой сводкой досье.
    """
    lines = []

    if faction is not None:
        lines.append(
            f"Ты служишь фракции '{faction.name}': чужие потери считай заслуженными."
        )
    if dossier.is_siege:
        lines.append("Это был штурм цитадели - событие, которое запомнят надолго.")
    if dossier.is_massacre:
        lines.append("Одну из сторон вырезали почти полностью: это была резня.")

    return [
        ContextBlock(title="Твое положение", body="\n".join(f"- {line}" for line in lines))
    ]
