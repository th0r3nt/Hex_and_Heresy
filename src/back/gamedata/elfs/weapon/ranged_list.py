"""
Реестр оружия дальнего боя фракции эльфов.
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

RANGED_WEAPONS: dict[str, dict[str, Any]] = {
    ElfsWeaponId.EMERALD_BOWS_01.value: {
        "id": ElfsWeaponId.EMERALD_BOWS_01.value,
        "name": "Изумрудные луки",
        "lore": "Тятива сплетена из энергии. Выпускают стрелы из уплотненного света, которые никогда не сдувает ветром.",
        "slot": _SLOT,
        "category": WeaponCategory.BOW,
        "tier": 1,
        "tags": {
            EquipmentTag.TWO_HANDED,
            EquipmentTag.RESONITE_POWERED,
        },  # Не STRING_BASED, дождь им не страшен
        "cost_gold": 8.0,
        "cost_material": 10.0,
        "stats": EquipmentStats(
            damage=10.0,
            range_hexes=7,
            armor_piercing=2.0,
            initiative_modifier=3,  # Высочайшая скорость стрельбы
        ),
        "special_rules": "Абсолютная точность: эльфийские стрелки всегда имеют наивысший приоритет инициативы.",
    },
    ElfsWeaponId.FOCUSING_SPHERES_02.value: {
        "id": ElfsWeaponId.FOCUSING_SPHERES_02.value,
        "name": "Фокусирующие сферы",
        "lore": "Эльф не атакует физически. Он выстреливает пучками плазмы прямо из левитирующей сферы, игнорируя людские щиты.",
        "slot": _SLOT,
        "category": WeaponCategory.MAGIC,
        "tier": 2,
        "tags": {EquipmentTag.ONE_HANDED, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 15.0,
        "cost_material": 20.0,
        "stats": EquipmentStats(
            damage=18.0,
            range_hexes=4,  # Средняя дистанция, но пробивает почти все
            armor_piercing=15.0,
        ),
        "special_rules": "Плазменный сгусток: наносит магический урон, который полностью игнорирует физические щиты (павезы, деревянные доски).",
    },
    ElfsWeaponId.KRON_KERN_GREATBOWS_03.value: {
        "id": ElfsWeaponId.KRON_KERN_GREATBOWS_03.value,
        "name": "Великие луки Крон-Керна",
        "lore": "Оружие-легенда. Энергетическая стрела сама ищет микроскопические уязвимости в латах.",
        "slot": _SLOT,
        "category": WeaponCategory.BOW,
        "tier": 3,
        "tags": {EquipmentTag.TWO_HANDED, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 30.0,
        "cost_material": 40.0,
        "stats": EquipmentStats(
            damage=25.0,
            range_hexes=10,  # Огромная дистанция
            armor_piercing=40.0,  # Игнорирует 80% брони
            initiative_modifier=-2,  # Долго заряжается
        ),
        "special_rules": "Снайперский алгоритм: стреляют сквозь лес без штрафов к урону и игнорируют броню тяжелой пехоты.",
    },
    ElfsWeaponId.DISTORTION_CANNONS_04.value: {
        "id": ElfsWeaponId.DISTORTION_CANNONS_04.value,
        "name": "Орудия Искажения",
        "lore": "Устанавливаются на Призрачные Ковчеги. Бьют антигравитационной волной, от которой враги падают на землю, задыхаясь от усталости.",
        "slot": _SLOT,
        "category": WeaponCategory.SIEGE_ENGINE,
        "tier": 4,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 50.0,
        "cost_material": 100.0,
        "stats": EquipmentStats(
            damage=10.0,  # Прямой урон небольшой
            range_hexes=8,
        ),
        "special_rules": "Гравитационный удар (AoE): вместо обычного урона, выстрел сжигает почти всю Выносливость вражеских отрядов в радиусе 1 гекса.",
    },
    ElfsWeaponId.TOXIC_GLANDS_05.value: {
        "id": ElfsWeaponId.TOXIC_GLANDS_05.value,
        "name": "Токсичные железы драконов",
        "lore": "Облако едкой кислоты, выдыхаемое мутировавшими драконами. Расщепляет плоть и имперскую сталь одинаково легко.",
        "slot": _SLOT,
        "category": WeaponCategory.NATURAL,
        "tier": 5,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 0.0,
        "cost_material": 0.0,
        "stats": EquipmentStats(
            damage=45.0,
            range_hexes=3,
        ),
        "special_rules": "Кислотный туман (AoE): полностью уничтожает показатель брони у всех врагов в зоне поражения до конца текущего боя.",
    },
}
