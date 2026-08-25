from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.models.context import ContextBlock

def build_faction_block(faction: Faction) -> ContextBlock:
    gold = faction.resources.get(ResourceType.GOLD, 0.0)
    food = faction.resources.get(ResourceType.FOOD, 0.0)
    material = faction.resources.get(ResourceType.MATERIAL, 0.0)
    
    lines = [
        f"Фракция: {faction.name} (Раса: {faction.race.value}).",
        f"Казна: {gold:.1f} золота, {material:.1f} материалов, {food:.1f} провизии."
    ]
    
    # Добавляем триггеры внимания для LLM
    if food < 50.0:
        lines.append("Внимание: Фракция страдает от нехватки провизии, войска могут начать голодать.")
    if gold < 20.0:
        lines.append("Внимание: Казна пуста, возможны задержки жалования и дезертирство.")
        
    return ContextBlock(
        title="Экономика фракции",
        body="\n".join(f"- {line}" for line in lines)
    )