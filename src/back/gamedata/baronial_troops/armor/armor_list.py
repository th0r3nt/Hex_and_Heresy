"""
Реестр брони фракции баронских войск.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    ArmorCategory,
    EquipmentSlot,
    EquipmentTag,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.baronial_troops.common import BaronialArmorId

_SLOT = EquipmentSlot.ARMOR

ARMOR_LIST: dict[str, dict[str, Any]] = {
    BaronialArmorId.TORN_CAFTANS_00.value: {
        "id": BaronialArmorId.TORN_CAFTANS_00.value,
        "name": "Рваные кафтаны",
        "lore": "Обычная одежда из мешковины. Защищает разве что от холодного ветра, но никак не от стрел или топоров.",
        "slot": _SLOT,
        "category": ArmorCategory.UNARMORED,
        "tier": 0,
        "cost_gold": 0.0,
        "cost_material": 0.5,
        "stats": EquipmentStats(armor_bonus=0.0),
    },
    BaronialArmorId.THICK_GAMBESON_00.value: {
        "id": BaronialArmorId.THICK_GAMBESON_00.value,
        "name": "Толстые стеганки",
        "lore": "Несколько слоев грязного льна, набитого конским волосом. Базовая защита, способная остановить случайный скользящий удар.",
        "slot": _SLOT,
        "category": ArmorCategory.PADDED,
        "tier": 0,
        "cost_gold": 0.5,
        "cost_material": 1.5,
        "stats": EquipmentStats(armor_bonus=1.5),
    },
    BaronialArmorId.DENSE_PADDED_JACKETS_01.value: {
        "id": BaronialArmorId.DENSE_PADDED_JACKETS_01.value,
        "name": "Плотные стеганые куртки",
        "lore": "Стоят дешево. От прямого удара мечом не спасут, но шальную стрелу, пущенную на излете, удержать могут.",
        "slot": _SLOT,
        "category": ArmorCategory.PADDED,
        "tier": 1,
        "cost_gold": 1.0,
        "cost_material": 2.0,
        "stats": EquipmentStats(armor_bonus=2.5),
    },
    BaronialArmorId.WORN_BRIGANDINE_02.value: {
        "id": BaronialArmorId.WORN_BRIGANDINE_02.value,
        "name": "Потертые бригантины",
        "lore": "Стандартная броня наемного пехотинца, купленная на барахолке или снятая с трупа.",
        "slot": _SLOT,
        "category": ArmorCategory.BRIGANDINE,
        "tier": 2,
        "cost_gold": 3.0,
        "cost_material": 4.0,
        "stats": EquipmentStats(armor_bonus=4.5),
    },
    BaronialArmorId.CASTLE_HALF_PLATE_02.value: {
        "id": BaronialArmorId.CASTLE_HALF_PLATE_02.value,
        "name": "Замковые полулаты",
        "lore": "Поцарапанные, грубо подогнанные доспехи, собранные из имперских трофеев. Хорошо держат рубящие удары.",
        "slot": _SLOT,
        "category": ArmorCategory.PLATE,
        "tier": 2,
        "tags": {EquipmentTag.HEAVY},
        "cost_gold": 4.0,
        "cost_material": 6.0,
        "stats": EquipmentStats(
            armor_bonus=6.0,
            speed_modifier=-0.1,
            stamina_drain_per_turn=1.0,
        ),
    },
    BaronialArmorId.EXECUTIONER_APRON_03.value: {
        "id": BaronialArmorId.EXECUTIONER_APRON_03.value,
        "name": "Фартук палача",
        "lore": "Плотный кожаный фартук поверх черной кольчуги. Униформа палачей. Тяжелая, но не сковывает широких замахов.",
        "slot": _SLOT,
        "category": ArmorCategory.LEATHER,
        "tier": 3,
        "cost_gold": 5.0,
        "cost_material": 5.0,
        "stats": EquipmentStats(
            armor_bonus=5.0,
            initiative_modifier=1,
        ),
    },
    BaronialArmorId.HANGING_GATES_04.value: {
        "id": BaronialArmorId.HANGING_GATES_04.value,
        "name": "Навесные ворота",
        "lore": "Огр баронства зашивается в металлолом: куски дубовых ворот и корабельных листов примотаны цепями к его плечам и груди.",
        "slot": _SLOT,
        "category": ArmorCategory.PLATE,
        "tier": 4,
        "tags": {EquipmentTag.HEAVY},
        "cost_gold": 10.0,
        "cost_material": 25.0,
        "stats": EquipmentStats(
            armor_bonus=18.0,
            speed_modifier=-0.2,
        ),
        "special_rules": "Живой щит: дает огру иммунитет к легкому дальнобойному оружию (обычные стрелы отскакивают от листов).",
    },
    BaronialArmorId.DESERTER_KNIGHT_PLATE_05.value: {
        "id": BaronialArmorId.DESERTER_KNIGHT_PLATE_05.value,
        "name": "Трофейные рыцарские латы",
        "lore": "Тяжелый стальной доспех, принадлежавший имперскому офицеру. Гербы сбиты зубилом, но защита осталась королевской.",
        "slot": _SLOT,
        "category": ArmorCategory.PLATE,
        "tier": 5,
        "tags": {EquipmentTag.HEAVY},
        "cost_gold": 12.0,
        "cost_material": 18.0,
        "stats": EquipmentStats(
            armor_bonus=16.0,
            speed_modifier=-0.15,
            stamina_drain_per_turn=2.0,
        ),
    },
    BaronialArmorId.BARONIAL_CARRIAGE_ARMOR_06.value: {
        "id": BaronialArmorId.BARONIAL_CARRIAGE_ARMOR_06.value,
        "name": "Баронская броня",
        "lore": "Стены кареты обиты бархатом и свинцом. Это поглощает кинетический урон и защищает жирную тушу барона от магических аномалий.",
        "slot": _SLOT,
        "category": ArmorCategory.CARAPACE,
        "tier": 6,
        "tags": {EquipmentTag.HEAVY},
        "cost_gold": 80.0,
        "cost_material": 100.0,
        "stats": EquipmentStats(
            armor_bonus=25.0,
            speed_modifier=-0.3,  # Карета очень медленная
        ),
    },
}
