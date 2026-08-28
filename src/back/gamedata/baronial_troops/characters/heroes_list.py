"""
Реестр легендарных героев баронств.

Лор личностей - docs/factions/baronial_troops/heroes.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/baronial_troops/heroes/.
"""

from typing import Any

from src.back.gamedata.baronial_troops.common import BaronialHeroId
from src.back.l01_domain.common import FactionRace, MechanicalModifier, StatName

_RACE = FactionRace.BARONIAL_TROOPS
_PROMPTS = "unique_personalities.baronial_troops.heroes"

HEROES_LIST: dict[str, dict[str, Any]] = {
    BaronialHeroId.SENESCHAL_GOTTFRIED.value: {
        "id": BaronialHeroId.SENESCHAL_GOTTFRIED.value,
        "race": _RACE,
        "name": "Сенешаль Готфрид",
        "archetype": "Безжалостный бюрократ",
        "prompt_ref": f"{_PROMPTS}.Seneschal_Gottfried",
        "trait_ids": ["bureaucrat", "greedy", "pragmatist"],
        "max_hp": 150.0,
        "special_rule": (
            "Смета боя: если убийство экономически невыгодно, Готфрид предлагает врагу "
            "откуп - раз в бой вражеский отряд низкого тира может выйти из сражения за золото."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.UPKEEP_GOLD, value=-0.2, is_percentage=True
        ),
        "lore_description": (
            "Тот, кто на самом деле управляет баронством, пока Барон пьет вино. Бархатный "
            "камзол поверх стальной кирасы, счетная книга с резонитовыми замками в одной руке "
            "и гравированный пистоль в другой. Жизнь крепостного стоит два серебряных."
        ),
    },
    BaronialHeroId.JUDGE_GAWAIN.value: {
        "id": BaronialHeroId.JUDGE_GAWAIN.value,
        "race": _RACE,
        "name": "Судья Гавейн",
        "archetype": "Садист в законе",
        "prompt_ref": f"{_PROMPTS}.Judge_Gawain",
        "trait_ids": ["sadist", "inquisitor", "bureaucrat"],
        "max_hp": 240.0,
        "special_rule": (
            "Приговор окончателен: добивая вражеский отряд, Гавейн наводит ужас на соседние "
            "с ним отряды противника, роняя их боевой дух."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.DAMAGE, value=0.3, is_percentage=True
        ),
        "lore_description": (
            "Огромный мужчина в белоснежном (до первой крови) судейском парике и кожаном "
            "фартуке. Вместо топора использует лезвие гильотины, приваренное к древку. "
            "Постоянно цитирует «Кодекс Баронства», где карается даже дыхание в сторону замка."
        ),
    },
    BaronialHeroId.BART_THE_ONE_EYED.value: {
        "id": BaronialHeroId.BART_THE_ONE_EYED.value,
        "race": _RACE,
        "name": "Барт Одноглазый",
        "archetype": "Егерь",
        "prompt_ref": f"{_PROMPTS}.Bart_the_One_Eyed",
        "trait_ids": ["cynic", "deserter", "paranoid"],
        "max_hp": 140.0,
        "special_rule": (
            "Сафари: капканы и волкодавы Барта замедляют первый вражеский отряд, вошедший "
            "в ближний бой с его армией, а отравленные болты не дают ранам затягиваться."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.AMBUSH_RESISTANCE, value=0.3, is_percentage=True
        ),
        "lore_description": (
            "Не благородных кровей: бывший браконьер, нанятый Бароном ловить беглых "
            "крепостных и дезертиров. Воюет так, чтобы враг его даже не видел - тяжелый "
            "арбалет с отравленными болтами, капканы и стая бронированных волкодавов."
        ),
    },
}
