from src.back.l01_domain.factions.constants import ResourceType, TaxPolicyBand
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.models.context import ContextBlock

# Как звучит для языковой модели настроение подданных при каждой ставке
TAX_BAND_MOOD: dict[TaxPolicyBand, str] = {
    TaxPolicyBand.HOLIDAY: "налоговые каникулы, народ боготворит правителя",
    TaxPolicyBand.REDUCED: "льготный сбор, подданные довольны",
    TaxPolicyBand.BASELINE: "базовая норма, общество спокойно",
    TaxPolicyBand.RAISED: "повышенные сборы, ропот в мастерских и возможны забастовки",
    TaxPolicyBand.PREDATORY: "грабительские поборы, земли на грани открытого бунта",
}


def build_faction_block(faction: Faction) -> ContextBlock:
    gold = faction.resources.get(ResourceType.GOLD, 0.0)
    food = faction.resources.get(ResourceType.FOOD, 0.0)
    material = faction.resources.get(ResourceType.MATERIAL, 0.0)
    
    mood = TAX_BAND_MOOD[faction.tax_band]

    lines = [
        f"Фракция: {faction.name} (Раса: {faction.race.value}).",
        f"Казна: {gold:.1f} золота, {material:.1f} материалов, {food:.1f} провизии.",
        f"Налоговая ставка: {faction.tax_rate:.1f} - {mood}.",
        f"Сбор налогов приносит {faction.tax_income_gold:.1f} золота за такт "
        f"(база: {faction.taxable_base_gold:.1f})."
    ]
    
    # Добавляем триггеры внимания для LLM
    if food < 50.0:
        lines.append("Внимание: Фракция страдает от нехватки провизии, войска могут начать голодать.")
    if gold < 20.0:
        lines.append("Внимание: Казна пуста, возможны задержки жалования и дезертирство.")
    if faction.tax_band == TaxPolicyBand.PREDATORY:
        lines.append(
            "Внимание: Ставка налога грабительская - крестьяне могут поднять восстание."
        )
        
    return ContextBlock(
        title="Экономика фракции",
        body="\n".join(f"- {line}" for line in lines)
    )