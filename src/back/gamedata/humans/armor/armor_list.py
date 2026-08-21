"""
Реестр брони фракции людей.
"""

from typing import Any

from src.back.l01_domain.army.constants import (
    ArmorCategory,
    EquipmentSlot,
    EquipmentTag,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.gamedata.humans.common import HumanArmorId

_SLOT = EquipmentSlot.ARMOR

ARMOR_LIST: dict[str, dict[str, Any]] = {
    HumanArmorId.WORKER_ROBES_00.value: {
        "id": HumanArmorId.WORKER_ROBES_00.value,
        "name": "Рабочие робы",
        "lore": "Обычная одежда из грубого льна. Защищает только от холода.",
        "slot": _SLOT,
        "category": ArmorCategory.CLOTH,
        "tier": 0,
        "cost_gold": 0.0,
        "cost_material": 0.5,
        "stats": EquipmentStats(armor_bonus=0.0),
    },
    HumanArmorId.HAIRSHIRTS_00.value: {
        "id": HumanArmorId.HAIRSHIRTS_00.value,
        "name": "Власяницы и цепи",
        "lore": "Не столько защищают, сколько вводят в религиозный экстаз через постоянную боль.",
        "slot": _SLOT,
        "category": ArmorCategory.CLOTH,
        "tier": 0,
        "cost_gold": 0.0,
        "cost_material": 1.0,
        "stats": EquipmentStats(armor_bonus=1.0),
        "special_rules": "Фанатизм: уменьшает потерю морали от получения урона на 50%.",
    },
    HumanArmorId.PADDED_JACKETS_01.value: {
        "id": HumanArmorId.PADDED_JACKETS_01.value,
        "name": "Стеганые куртки",
        "lore": "Много слоев плотной ткани. Отлично защищают от скользящих ударов крестьян и гоблинов.",
        "slot": _SLOT,
        "category": ArmorCategory.PADDED,
        "tier": 1,
        "cost_gold": 0.5,
        "cost_material": 2.0,
        "stats": EquipmentStats(armor_bonus=3.0),
    },
    HumanArmorId.LEATHER_BREASTPLATES_01.value: {
        "id": HumanArmorId.LEATHER_BREASTPLATES_01.value,
        "name": "Кожаные нагрудники",
        "lore": "Очень легкие доспехи. Не дают штрафов к выносливости, идеальны для стрелков.",
        "slot": _SLOT,
        "category": ArmorCategory.LEATHER,
        "tier": 1,
        "cost_gold": 1.0,
        "cost_material": 2.0,
        "stats": EquipmentStats(armor_bonus=2.0),
    },
    HumanArmorId.STEEL_CUIRASSES_02.value: {
        "id": HumanArmorId.STEEL_CUIRASSES_02.value,
        "name": "Стальные кирасы",
        "lore": "Тяжелая монолитная защита торса. Снижает скорость передвижения, но отлично держит рубящие удары.",
        "slot": _SLOT,
        "category": ArmorCategory.PLATE,
        "tier": 2,
        "tags": {EquipmentTag.HEAVY},
        "cost_gold": 4.0,
        "cost_material": 6.0,
        "stats": EquipmentStats(
            armor_bonus=6.0,
            speed_modifier=-0.1,  # -10% к скорости
            stamina_drain_per_turn=0.5,
        ),
    },
    HumanArmorId.CAVALRY_MAIL_02.value: {
        "id": HumanArmorId.CAVALRY_MAIL_02.value,
        "name": "Кавалерийская кольчуга",
        "lore": "Специально подогнана для езды верхом. Не сковывает движений ног.",
        "slot": _SLOT,
        "category": ArmorCategory.MAIL,
        "tier": 2,
        "cost_gold": 5.0,
        "cost_material": 4.0,
        "stats": EquipmentStats(armor_bonus=5.0),
    },
    HumanArmorId.HEAVY_HALF_PLATE_03.value: {
        "id": HumanArmorId.HEAVY_HALF_PLATE_03.value,
        "name": "Тяжелые полулаты",
        "lore": "Непробиваемы для легкого оружия, но отряд в них быстро задыхается в затяжном ближнем бою.",
        "slot": _SLOT,
        "category": ArmorCategory.PLATE,
        "tier": 3,
        "tags": {EquipmentTag.HEAVY},
        "cost_gold": 8.0,
        "cost_material": 10.0,
        "stats": EquipmentStats(
            armor_bonus=10.0,
            initiative_modifier=-2,
            speed_modifier=-0.15,
            stamina_drain_per_turn=1.5,
        ),
    },
    HumanArmorId.PURITY_RUNE_CLOAKS_03.value: {
        "id": HumanArmorId.PURITY_RUNE_CLOAKS_03.value,
        "name": "Плащи с рунами очищения",
        "lore": "Специальная униформа Охотников на ведьм. Отводит от владельца гибельное излучение резонита.",
        "slot": _SLOT,
        "category": ArmorCategory.CLOTH,
        "tier": 3,
        "tags": {EquipmentTag.SILVER},
        "cost_gold": 10.0,
        "cost_material": 4.0,
        "stats": EquipmentStats(armor_bonus=2.0),
        "special_rules": "Антимагия: дает 30% сопротивления магическому урону.",
    },
    HumanArmorId.FULL_KNIGHT_PLATE_04.value: {
        "id": HumanArmorId.FULL_KNIGHT_PLATE_04.value,
        "name": "Полные рыцарские латы",
        "lore": "Превращают отряд в ходячие стальные танки. Защищают даже от выстрелов из аркебуз на дальних дистанциях.",
        "slot": _SLOT,
        "category": ArmorCategory.PLATE,
        "tier": 4,
        "tags": {EquipmentTag.HEAVY},
        "cost_gold": 15.0,
        "cost_material": 18.0,
        "stats": EquipmentStats(
            armor_bonus=18.0,
            initiative_modifier=-4,
            speed_modifier=-0.2,
            stamina_drain_per_turn=2.5,
        ),
    },
    HumanArmorId.RELIQUARY_ARMOR_05.value: {
        "id": HumanArmorId.RELIQUARY_ARMOR_05.value,
        "name": "Реликварный доспех",
        "lore": "Выкован из метеоритного железа. На каждой пластине выгравированы имена павших святых Инквизиции.",
        "slot": _SLOT,
        "category": ArmorCategory.PLATE,
        "tier": 5,
        "tags": {EquipmentTag.HEAVY, EquipmentTag.SILVER},
        "cost_gold": 25.0,
        "cost_material": 20.0,
        "stats": EquipmentStats(
            armor_bonus=25.0,
            initiative_modifier=-2,
        ),
        "special_rules": "Абсолютная вера: носитель получает полную невосприимчивость к любым эффектам страха и паники.",
    },
}
