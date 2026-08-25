from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.world.models.state import WorldState

def build_world_block(world_state: WorldState) -> ContextBlock:
    lines = [
        f"Текущее время: {world_state.time.format_timestamp()}.",
        f"Тактов без боев: {world_state.ticks_since_last_battle}.",
    ]
    
    active_events = [e for e in world_state.active_events if e.is_active]
    if active_events:
        events_str = ", ".join(f"«{e.name}»" for e in active_events[:5])
        lines.append(f"Активные глобальные события: {events_str}.")

    battlefields = [s for s in world_state.battlefield_sites.values() if not s.is_depleted]
    if battlefields:
        lines.append(f"На карте гниют поля брани: {len(battlefields)}.")
        
    return ContextBlock(
        title="Обстановка в мире",
        body="\n".join(f"- {line}" for line in lines)
    )