"""
Реестр аксессуаров фракции эльфов.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    AccessoryCategory,
    EquipmentSlot,
    EquipmentTag,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.elfs.common import ElfsAccessoryId

_SLOT = EquipmentSlot.ACCESSORY

ACCESSORIES_LIST: dict[str, dict[str, Any]] = {
    ElfsAccessoryId.FORESIGHT_LENSES_00.value: {
        "id": ElfsAccessoryId.FORESIGHT_LENSES_00.value,
        "name": "Линзы дальновидности",
        "lore": "Кристаллы, преломляющие свет так, что позволяют видеть на мили вперед, игнорируя туман и пепел.",
        "slot": _SLOT,
        "category": AccessoryCategory.MISC,
        "tier": 0,
        "cost_gold": 2.0,
        "cost_material": 4.0,
        "stats": EquipmentStats(range_hexes=1),
        "special_rules": "Тактическая разведка: значительно увеличивают радиус обзора отряда на стратегической и тактической картах.",
    },
    ElfsAccessoryId.FACELESS_MASKS_01.value: {
        "id": ElfsAccessoryId.FACELESS_MASKS_01.value,
        "name": "Маски Безликих",
        "lore": "Гладкие резонитовые шлемы без прорезей для глаз. Эльфы видят мир через магические частоты, игнорируя ужасы поля боя.",
        "slot": _SLOT,
        "category": AccessoryCategory.MISC,
        "tier": 1,
        "cost_gold": 5.0,
        "cost_material": 5.0,
        "stats": EquipmentStats(initiative_modifier=1),
        "special_rules": "Хладнокровие: дает полный иммунитет к механикам 'Страха', вызванным видом разорванных трупов или монстров.",
    },
    ElfsAccessoryId.MIRAGE_PRISM_02.value: {
        "id": ElfsAccessoryId.MIRAGE_PRISM_02.value,
        "name": "Призма-мираж",
        "lore": "Кристалл, проецирующий объемную голограмму отряда на несколько метров в сторону.",
        "slot": _SLOT,
        "category": AccessoryCategory.TRAP,
        "tier": 2,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 10.0,
        "cost_material": 15.0,
        "stats": EquipmentStats(),
        "special_rules": "Иллюзия цели: враг, совершающий 'Натиск' на этот отряд, имеет 40% шанс влететь в фантом, растратив выносливость в пустоту.",
    },
    ElfsAccessoryId.ACCUMULATOR_MIRRORS_03.value: {
        "id": ElfsAccessoryId.ACCUMULATOR_MIRRORS_03.value,
        "name": "Зеркала-накопители",
        "lore": "Парят вокруг мага, пассивно собирая энергетический фон из воздуха.",
        "slot": _SLOT,
        "category": AccessoryCategory.RELIC,
        "tier": 3,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 15.0,
        "cost_material": 25.0,
        "stats": EquipmentStats(damage=5.0),
    },
    ElfsAccessoryId.RESONANT_TUNING_FORK_03.value: {
        "id": ElfsAccessoryId.RESONANT_TUNING_FORK_03.value,
        "name": "Резонансный камертон",
        "lore": "Звенит на ультра-высокой ноте, физически разрывающей нейронные связи примитивных созданий.",
        "slot": _SLOT,
        "category": AccessoryCategory.INSTRUMENT,
        "tier": 3,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 10.0,
        "cost_material": 20.0,
        "stats": EquipmentStats(),
        "special_rules": "Сбой инстинктов: дезориентирует существ с чутким слухом (собак, волков, оборотней) в радиусе 1 гекса, заставляя их иногда атаковать свои же войска.",
    },
    ElfsAccessoryId.RESONATING_STONE_04.value: {
        "id": ElfsAccessoryId.RESONATING_STONE_04.value,
        "name": "Резонирующий камень",
        "lore": "Синхронизирует души экипажа Ковчега. Для эльфов смерть — это лишь возврат в информационное поле.",
        "slot": _SLOT,
        "category": AccessoryCategory.RELIC,
        "tier": 4,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 40.0,
        "cost_material": 50.0,
        "stats": EquipmentStats(),
        "special_rules": "Сохранение сущности: если этот отряд погибает, 100% его базовой стоимости возвращается в казну.",
    },
    ElfsAccessoryId.DEW_OF_THE_PROGENITOR_05.value: {
        "id": ElfsAccessoryId.DEW_OF_THE_PROGENITOR_05.value,
        "name": "Флаконы с росой Прародителя",
        "lore": "Конденсированная жидкая магия. Мгновенно заращивает любые раны, но навсегда выжигает часть клеток носителя.",
        "slot": _SLOT,
        "category": AccessoryCategory.POTION,
        "tier": 5,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 30.0,
        "cost_material": 80.0,
        "stats": EquipmentStats(),
        "special_rules": "Радикальное исцеление: можно использовать раз за бой для мгновенного исцеления отряда, но максимальная выносливость навсегда снижается на 15%.",
    },
    ElfsAccessoryId.GRAVITY_COLLAPSAR_06.value: {
        "id": ElfsAccessoryId.GRAVITY_COLLAPSAR_06.value,
        "name": "Гравитационный коллапсар",
        "lore": "Сдерживающий механизм в груди Небесного полководца. Смерть носителя отключает предохранители.",
        "slot": _SLOT,
        "category": AccessoryCategory.RELIC,
        "tier": 6,
        "tags": {EquipmentTag.RESONITE_POWERED},
        "cost_gold": 200.0,
        "cost_material": 400.0,
        "stats": EquipmentStats(),
        "special_rules": "Сингулярность: при гибели отряда затягивает все вражеские карточки из соседних гексов в эпицентр ядерно-магического взрыва. Шансов убежать нет.",
    },
}
