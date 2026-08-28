"""
Реестр легендарных героев фракции зеленокожих.

Лор личностей - docs/factions/greenskins/heroes.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/greenskins/heroes/.
"""

from typing import Any

from src.back.gamedata.greenskins.common import GreenskinsHeroId
from src.back.l01_domain.common import FactionRace, MechanicalModifier, StatName

_RACE = FactionRace.GREENSKINS
_PROMPTS = "unique_personalities.greenskins.heroes"

HEROES_LIST: dict[str, dict[str, Any]] = {
    GreenskinsHeroId.GROM_IRONBELLY.value: {
        "id": GreenskinsHeroId.GROM_IRONBELLY.value,
        "race": _RACE,
        "name": 'Гром "Железное брюхо"',
        "archetype": "Неубиваемый",
        "prompt_ref": f"{_PROMPTS}.Grom_Ironbelly",
        "trait_ids": ["megalomaniac", "hyperplasia", "gladiator"],
        "max_hp": 340.0,
        "special_rule": (
            "Вера в бессмертие: первое смертельное ранение за бой Гром просто не замечает - "
            "он остается в строю с минимальным запасом здоровья."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.HP_REGEN, value=6.0, is_percentage=False
        ),
        "lore_description": (
            "Выжил после прямого попадания 12-фунтового имперского ядра: оно застряло у него "
            "в животе, и грибковая физиология орков обросла вокруг. Носит броню из кусков "
            "вражеских осадных орудий и уважает только тех, кто бьет сильнее него."
        ),
    },
    GreenskinsHeroId.SNAGA_STICKY_HANDS.value: {
        "id": GreenskinsHeroId.SNAGA_STICKY_HANDS.value,
        "race": _RACE,
        "name": 'Снага "Липкие Руки"',
        "archetype": "Гений-счетовод",
        "prompt_ref": f"{_PROMPTS}.Snaga_Sticky_Hands",
        "trait_ids": ["greedy", "cynic", "craven"],
        "max_hp": 150.0,
        "special_rule": (
            "Хозяйский глаз: пока Снага в армии, эта армия собирает с полей брани заметно "
            "больше трофейной экипировки и металлолома."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.UPKEEP_GOLD, value=-0.15, is_percentage=True
        ),
        "lore_description": (
            "Пока орки рубят головы, Снага собирает лут. Один из немногих зеленокожих, кто "
            "умеет (плохо) считать и понимает ценность золота. Ездит на бронированной повозке, "
            "собранной по украденным у имперской мануфактуры чертежам."
        ),
    },
    GreenskinsHeroId.UG_AND_GLUG.value: {
        "id": GreenskinsHeroId.UG_AND_GLUG.value,
        "race": _RACE,
        "name": "Двуглавый Уг-и-Глуг",
        "archetype": "Неудачный эксперимент",
        "prompt_ref": f"{_PROMPTS}.Ug_and_Glug",
        "trait_ids": ["chaos", "hyperplasia", "vengeful"],
        "max_hp": 280.0,
        "special_rule": (
            "Две головы, одно тело: каждый раунд боя существо действует либо как безмозглый "
            "таран Уга, либо как расчетливая магия Глуга - что именно, решает бросок."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.DAMAGE, value=0.3, is_percentage=True
        ),
        "lore_description": (
            "Гоблин-шаман Глуг сидел в корзине на спине огра Уга, когда в них попало "
            "эльфийское заклинание, искаженное резонитом. Тела сплавились: из горба огра растет "
            "светящаяся голова гоблина. Они ненавидят друг друга, но делят одну кровь."
        ),
    },
}
