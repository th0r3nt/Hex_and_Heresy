"""
Реестр оружия ближнего боя фракции эльфов.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    EquipmentSlot,
    EquipmentTag,
    WeaponCategory,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.elfs.common import ElfsWeaponId

_SLOT = EquipmentSlot.WEAPON

MELEE_WEAPONS: dict[str, dict[str, Any]] = {
    ElfsWeaponId.IRONWOOD_STAFF_00.value: {
        "id": ElfsWeaponId.IRONWOOD_STAFF_00.value,
        "name": "Резные посохи из железного дерева",
        "lore": "Практически не наносят урона бронированным целям. Ученики используют их скорее для медитаций и самообороны от диких зверей.",
        "slot": _SLOT,
        "category": WeaponCategory.POLEARM,
        "tier": 0,
        "tags": {EquipmentTag.TWO_HANDED},
        "cost_gold": 0.0,
        "cost_material": 2.0,
        "stats": EquipmentStats(
            damage=3.0,
            armor_piercing=0.0,
        ),
    },
    ElfsWeaponId.CRYSTAL_DAGGERS_00.value: {
        "id": ElfsWeaponId.CRYSTAL_DAGGERS_00.value,
        "name": "Хрустальные кинжалы",
        "lore": "Хрупкие лезвия из неочищенного резонита. Ломаются о сталь, оставляя ядовитые осколки в плоти врага.",
        "slot": _SLOT,
        "category": WeaponCategory.DAGGER,
        "tier": 0,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 1.0,
        "cost_material": 3.0,
        "stats": EquipmentStats(
            damage=5.0,
            armor_piercing=5.0,  # Осколки легко пробивают легкую броню
            initiative_modifier=2,
        ),
    },
    ElfsWeaponId.PURE_CLEAVE_GLAIVES_01.value: {
        "id": ElfsWeaponId.PURE_CLEAVE_GLAIVES_01.value,
        "name": "Глефы чистого скола",
        "lore": "Резонитовые лезвия заточены на атомарном уровне. Оружие невероятно легкое, эльф не устает, размахивая им.",
        "slot": _SLOT,
        "category": WeaponCategory.POLEARM,
        "tier": 1,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 5.0,
        "cost_material": 8.0,
        "stats": EquipmentStats(
            damage=12.0,
            armor_piercing=6.0,
            range_hexes=2,
            stamina_drain_per_turn=0.0,  # Эльфы не тратят доп. выносливость на эти клинки
        ),
    },
    ElfsWeaponId.TWIN_MOONBLADES_02.value: {
        "id": ElfsWeaponId.TWIN_MOONBLADES_02.value,
        "name": "Сдвоенные лунные клинки",
        "lore": "Парные мечи изогнутой формы. Танцующие-с-клинками наносят ими десятки порезов за секунду, превращая бой в смертельный танец.",
        "slot": _SLOT,
        "category": WeaponCategory.SWORD,
        "tier": 2,
        "tags": {EquipmentTag.ONE_HANDED},
        "cost_gold": 10.0,
        "cost_material": 12.0,
        "stats": EquipmentStats(
            damage=16.0,
            initiative_modifier=4,
        ),
        "special_rules": "Двойной удар: Идеальны против толп с нулевой броней. Наносят удвоенное количество атак (встроено в базовый урон).",
    },
    ElfsWeaponId.LIQUID_LIGHT_WHIPS_03.value: {
        "id": ElfsWeaponId.LIQUID_LIGHT_WHIPS_03.value,
        "name": "Хлысты жидкого света",
        "lore": "Отсекают конечности сквозь узкие щели в броне. Вызывают панику у тяжелобронированных рыцарей, привыкших к неуязвимости.",
        "slot": _SLOT,
        "category": WeaponCategory.WHIP,
        "tier": 3,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 20.0,
        "cost_material": 18.0,
        "stats": EquipmentStats(
            damage=20.0,
            armor_piercing=15.0,  # Жидкий свет легко проникает под латы
            range_hexes=2,
            initiative_modifier=2,
        ),
        "special_rules": "Шок света: попадания этим оружием наносят дополнительный урон по морали цели.",
    },
    ElfsWeaponId.SUPERNOVA_SPEAR_06.value: {
        "id": ElfsWeaponId.SUPERNOVA_SPEAR_06.value,
        "name": "Копье Сверхновой",
        "lore": "Сотканное из чистого излучения Прародителя. Любая плоть, пронзенная им, распадается на Первичную взвесь.",
        "slot": _SLOT,
        "category": WeaponCategory.SPEAR,
        "tier": 6,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 100.0,
        "cost_material": 200.0,
        "stats": EquipmentStats(
            damage=150.0,
            armor_piercing=100.0,
            initiative_modifier=5,
        ),
        "special_rules": "Распад: убитый этим копьем отряд накладывает радиационный дебафф на соседние клетки, отравляя окружающих.",
    },
}
