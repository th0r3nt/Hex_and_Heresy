"""
Реестр сборки армий (Ростер) фракции наемников.
Их найм стоит исключительно золота, они продают свои услуги на глобальной карте как готовые контракты.
"""

from typing import Any

from src.back.gamedata.mercenaries.common import (
    MercenaryAccessoryId,
    MercenaryArmorId,
    MercenaryRosterId,
    MercenaryUnitId,
    MercenaryWeaponId,
)

_FACTION = "mercenaries"

ROSTER_LIST: dict[str, dict[str, Any]] = {
    MercenaryRosterId.CONTRACT_FREE_COMPANY.value: {
        "id": MercenaryRosterId.CONTRACT_FREE_COMPANY.value,
        "faction_id": _FACTION,
        "unit_archetype_id": MercenaryUnitId.FREE_COMPANY_01.value,
        "weapon_id": MercenaryWeaponId.COMPANY_CROSSBOW_01.value,
        "armor_id": MercenaryArmorId.COMPANY_BRIGANDINE_01.value,
        "accessory_id": MercenaryAccessoryId.ADVANCE_PAYMENT_01.value,
        "cost_gold": 25.0, # Контракт I уровня
        "cost_material": 0.0,
    },
    MercenaryRosterId.CONTRACT_BEAR_TAMERS.value: {
        "id": MercenaryRosterId.CONTRACT_BEAR_TAMERS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": MercenaryUnitId.BEAR_TAMERS_01.value,
        "weapon_id": MercenaryWeaponId.BEAR_CLAWS_01.value,
        "armor_id": MercenaryArmorId.BEAR_BARDING_01.value,
        "accessory_id": MercenaryAccessoryId.TAMER_WHIP_01.value,
        "cost_gold": 30.0, # Контракт I уровня
        "cost_material": 5.0,
    },
    MercenaryRosterId.CONTRACT_HEROES.value: {
        "id": MercenaryRosterId.CONTRACT_HEROES.value,
        "faction_id": _FACTION,
        "unit_archetype_id": MercenaryUnitId.HEROES_FOR_HIRE_02.value,
        "weapon_id": MercenaryWeaponId.HEROIC_ARSENAL_02.value,
        "armor_id": MercenaryArmorId.ADVENTURER_GEAR_02.value,
        "accessory_id": MercenaryAccessoryId.QUEST_ARTIFACT_02.value,
        "cost_gold": 60.0, # Контракт II уровня
        "cost_material": 20.0, # Требуют материалы-артефакты
    },
    MercenaryRosterId.CONTRACT_CORSAIRS.value: {
        "id": MercenaryRosterId.CONTRACT_CORSAIRS.value,
        "faction_id": _FACTION,
        "unit_archetype_id": MercenaryUnitId.CORSAIRS_03.value,
        "weapon_id": MercenaryWeaponId.AERIAL_BOMBS_03.value,
        "armor_id": MercenaryArmorId.ZEPPELIN_HULL_03.value,
        "accessory_id": MercenaryAccessoryId.BOMBSIGHT_03.value,
        "cost_gold": 120.0, # Контракт III уровня
        "cost_material": 30.0,
    },
}