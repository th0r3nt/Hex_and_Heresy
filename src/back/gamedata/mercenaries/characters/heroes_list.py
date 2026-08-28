"""
Реестр легендарных вольных капитанов.

У наемников нет ни лордов, ни полководцев: это нейтральная сила без
цитадели и правителя - точка на глобальной карте, у которой нанимают роты.
Поэтому характеров у них ровно три, и все они герои.

Лор личностей - docs/factions/mercenaries/heroes.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/mercenaries/heroes/.
"""

from typing import Any

from src.back.gamedata.mercenaries.common import MercenaryHeroId
from src.back.l01_domain.common import FactionRace, MechanicalModifier, StatName

_RACE = FactionRace.MERCENARIES
_PROMPTS = "unique_personalities.mercenaries.heroes"

HEROES_LIST: dict[str, dict[str, Any]] = {
    MercenaryHeroId.CAPTAIN_VANCE.value: {
        "id": MercenaryHeroId.CAPTAIN_VANCE.value,
        "race": _RACE,
        "name": "Капитан Вэнс",
        "archetype": "Командир дирижабля",
        "prompt_ref": f"{_PROMPTS}.Captain_Vance",
        "trait_ids": ["hedonist", "greedy", "cynic"],
        "max_hp": 150.0,
        "special_rule": (
            "Воздушное превосходство: армия под началом Вэнса заранее видит расположение "
            "вражеского строя перед боем и сбрасывает бомбы до первой фазы схватки."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.VISIBILITY_RANGE_CELLS, value=3.0, is_percentage=False
        ),
        "lore_description": (
            "Бывший главный инженер Цитадели, укравший чертежи первого дирижабля. Нанял "
            "банду гоблинов-дезертиров, потому что они легкие и не боятся высоты. Его "
            "цеппелин - летающий кабак, полный награбленного золота."
        ),
    },
    MercenaryHeroId.LADY_BEATRICE.value: {
        "id": MercenaryHeroId.LADY_BEATRICE.value,
        "race": _RACE,
        "name": "Леди Беатрис",
        "archetype": "Хозяйка тяжелой пехоты",
        "prompt_ref": f"{_PROMPTS}.Lady_Beatrice",
        "trait_ids": ["aristocrat", "vengeful", "pragmatist"],
        "max_hp": 230.0,
        "special_rule": (
            "«Слезы Вдовы» не отступают: отряды в армии Беатрис игнорируют первую проверку "
            "боевого духа в каждом бою."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.MORALE, value=12.0, is_percentage=False
        ),
        "lore_description": (
            "Жена барона, убитого эльфийскими ассасинами. Приказала переплавить парадные латы "
            "мужа в алебарду, продала замок и наняла лучших ветеранов Ничьей земли. "
            "Превратила месть в прибыльный бизнес: игрок для нее - не лорд, а клиент."
        ),
    },
    MercenaryHeroId.HECTOR.value: {
        "id": MercenaryHeroId.HECTOR.value,
        "race": _RACE,
        "name": "Гектор",
        "archetype": "Багряный сомелье",
        "prompt_ref": f"{_PROMPTS}.Hector",
        "trait_ids": ["desiccation", "hedonist", "aristocrat"],
        "max_hp": 210.0,
        "special_rule": (
            "Дегустация: убивая вражеский отряд в ближнем бою, Гектор восстанавливает часть "
            "собственного здоровья свежей плазмой."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.HP_REGEN, value=8.0, is_percentage=False
        ),
        "lore_description": (
            "Бывший правитель независимого баронства с Изъяном иссушения: костный мозг сгорел "
            "от магии, и он вынужден вливать в себя чужую плазму. Сделал из проклятия культ "
            "эстетики и стал наемником ради дегустации разных рас."
        ),
    },
}
