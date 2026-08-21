"""
Реестр брони фракции эльфов.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    ArmorCategory,
    EquipmentSlot,
    EquipmentTag,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.elfs.common import ElfsArmorId

_SLOT = EquipmentSlot.ARMOR

ARMOR_LIST: dict[str, dict[str, Any]] = {
    ElfsArmorId.GHOST_SILK_ROBES_00.value: {
        "id": ElfsArmorId.GHOST_SILK_ROBES_00.value,
        "name": "Одеяния из призрачного шелка",
        "lore": "Ткань отталкивает грязь и воду. От удара мечом не спасет, но позволяет эльфам не пачкать ноги в болотах Ничьей земли.",
        "slot": _SLOT,
        "category": ArmorCategory.CLOTH,
        "tier": 0,
        "cost_gold": 2.0,
        "cost_material": 3.0,
        "stats": EquipmentStats(armor_bonus=1.0),
        "special_rules": "Легкий шаг: отряд полностью игнорирует штрафы к скорости перемещения по грязи и болотам.",
    },
    ElfsArmorId.SINGING_RESIN_ARMOR_01.value: {
        "id": ElfsArmorId.SINGING_RESIN_ARMOR_01.value,
        "name": "Доспехи из поющей смолы",
        "lore": "Элегантная броня. При резком кинетическом ударе смола мгновенно кристаллизуется, поглощая урон, а затем снова становится гибкой.",
        "slot": _SLOT,
        "category": ArmorCategory.CARAPACE,
        "tier": 1,
        "cost_gold": 5.0,
        "cost_material": 8.0,
        "stats": EquipmentStats(armor_bonus=4.0),
    },
    ElfsArmorId.EMERALD_WYVERN_SCALES_02.value: {
        "id": ElfsArmorId.EMERALD_WYVERN_SCALES_02.value,
        "name": "Чешуя изумрудных виверн",
        "lore": "Легкие, переливающиеся пластины. Совершенно невосприимчивы к высоким температурам, но легко проминаются под ударом орочьей кувалды.",
        "slot": _SLOT,
        "category": ArmorCategory.LEATHER,
        "tier": 2,
        "cost_gold": 10.0,
        "cost_material": 15.0,
        "stats": EquipmentStats(armor_bonus=6.0),
        "special_rules": "Огнеупорность: дает полный иммунитет к урону от огня демонов и взрывов пороха.",
    },
    ElfsArmorId.SYMBIOTIC_CARAPACE_03.value: {
        "id": ElfsArmorId.SYMBIOTIC_CARAPACE_03.value,
        "name": "Симбиотический панцирь",
        "lore": "Резонит прорастает сквозь плоть воина, заменяя кожу на живой минерал. Дает феноменальную защиту ценой потери скорости.",
        "slot": _SLOT,
        "category": ArmorCategory.CARAPACE,
        "tier": 3,
        "tags": {EquipmentTag.HEAVY, EquipmentTag.RESONITE_POWERED},
        "cost_gold": 15.0,
        "cost_material": 25.0,
        "stats": EquipmentStats(
            armor_bonus=15.0,
            speed_modifier=-0.2,  # Единственная тяжелая броня эльфов
        ),
    },
    ElfsArmorId.REFRACTION_MANTLES_03.value: {
        "id": ElfsArmorId.REFRACTION_MANTLES_03.value,
        "name": "Мантии преломления",
        "lore": "Сложная оптическая иллюзия, вплетенная в ткань. Вражеские стрелки видят лишь размытые силуэты.",
        "slot": _SLOT,
        "category": ArmorCategory.CLOTH,
        "tier": 3,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 15.0,
        "cost_material": 30.0,
        "stats": EquipmentStats(armor_bonus=3.0),
        "special_rules": "Мираж: любые дальнобойные атаки по этому отряду промахиваются с базовым шансом 40%.",
    },
    ElfsArmorId.ARK_ENERGY_SHIELDS_04.value: {
        "id": ElfsArmorId.ARK_ENERGY_SHIELDS_04.value,
        "name": "Энергетические щиты",
        "lore": "Силовые поля, проецируемые парящим Ковчегом. Невидимая стена, обжигающая тех, кто пытается ее пробить.",
        "slot": _SLOT,
        "category": ArmorCategory.FORCE_FIELD,
        "tier": 4,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 30.0,
        "cost_material": 60.0,
        "stats": EquipmentStats(armor_bonus=10.0),
        "special_rules": "Регенерация поля: дает отряду временные ХП. Если отряд не получает урона один такт, щит восстанавливается.",
    },
    ElfsArmorId.ANTIGRAVITY_PLATE_05.value: {
        "id": ElfsArmorId.ANTIGRAVITY_PLATE_05.value,
        "name": "Пластина антигравитации",
        "lore": "Заменяет седло для драконов. Создает вокруг всадника искажение, отклоняющее любые мелкие медленные предметы.",
        "slot": _SLOT,
        "category": ArmorCategory.FORCE_FIELD,
        "tier": 5,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 50.0,
        "cost_material": 100.0,
        "stats": EquipmentStats(armor_bonus=12.0),
        "special_rules": "Абсолютное отклонение: игнорирует урон от любых луков и арбалетов (но пробивается артиллерией или магией).",
    },
    ElfsArmorId.SHROUD_OF_THE_ABSOLUTE_06.value: {
        "id": ElfsArmorId.SHROUD_OF_THE_ABSOLUTE_06.value,
        "name": "Пелена Абсолюта",
        "lore": "Сверхмассивный резонитовый кокон Небесного полководца. Одно его присутствие подавляет волю низших существ к сопротивлению.",
        "slot": _SLOT,
        "category": ArmorCategory.FORCE_FIELD,
        "tier": 6,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 150.0,
        "cost_material": 300.0,
        "stats": EquipmentStats(armor_bonus=30.0),
        "special_rules": "Благоговение: враги, находящиеся на соседней клетке, обязаны проходить проверку на дисциплину, иначе отказываются атаковать полководца в свой ход.",
    },
}
