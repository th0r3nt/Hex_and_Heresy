"""
Реестр легендарных героев фракции людей.

Лор личностей - docs/factions/humans/heroes.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/humans/heroes/.
"""

from typing import Any

from src.back.gamedata.humans.common import HumanHeroId
from src.back.l01_domain.common import FactionRace, MechanicalModifier, StatName

_RACE = FactionRace.HUMANS
_PROMPTS = "unique_personalities.humans.heroes"

HEROES_LIST: dict[str, dict[str, Any]] = {
    HumanHeroId.AUGUST_VON_LICHT.value: {
        "id": HumanHeroId.AUGUST_VON_LICHT.value,
        "race": _RACE,
        "name": "Август фон Лихт",
        "archetype": "Охотник на магов",
        "prompt_ref": f"{_PROMPTS}.August_von_Licht",
        "trait_ids": ["inquisitor", "vengeful", "paranoid"],
        "max_hp": 180.0,
        "special_rule": (
            "Ловчий ереси: вражеские отряды и герои с магическими способностями теряют "
            "боевой дух, пока Август находится в пределах видимости их строя."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.DAMAGE, value=0.25, is_percentage=True
        ),
        "lore_description": (
            "Потерял семью, когда соседская девочка-маг неконтролируемо воспламенила резонит. "
            "С тех пор носит глухую маску-фильтр от Первичной взвеси и считает любую магию "
            "болезнью, которую лечат сталью."
        ),
    },
    HumanHeroId.ELARA_VANCE.value: {
        "id": HumanHeroId.ELARA_VANCE.value,
        "race": _RACE,
        "name": "Элара Вэнс",
        "archetype": "Мастер огнестрела",
        "prompt_ref": f"{_PROMPTS}.Elara_Vance",
        "trait_ids": ["pragmatist", "cynic", "perfectionist"],
        "max_hp": 140.0,
        "special_rule": (
            "Залп в упор: стрелковые отряды в одном отряде с Эларой не получают штраф "
            "к точности на ближней дистанции и реже дают осечку."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.RANGED_ACCURACY, value=0.2, is_percentage=True
        ),
        "lore_description": (
            "Инженер Имперских мануфактур, пропахшая серой и пороховой гарью. Считает, что "
            "молитвы не останавливают огров, а 12-фунтовое ядро - вполне. Для мощного пороха "
            "тайно использует перетертый инертный резонит, что является ересью."
        ),
    },
    HumanHeroId.BAYLEN_THE_MAIMED.value: {
        "id": HumanHeroId.BAYLEN_THE_MAIMED.value,
        "race": _RACE,
        "name": "Сэр Бэйлен Изувеченный",
        "archetype": "Ищущий смерти",
        "prompt_ref": f"{_PROMPTS}.Sir_Baylen_the_Maimed",
        "trait_ids": ["fatalist", "aristocrat", "gladiator"],
        "max_hp": 320.0,  # Абсурдно толстая броня, которую он поклялся не снимать
        "special_rule": (
            "Искупление кровью: пока Бэйлен жив, отряд, к которому он прикреплен, не может "
            "запаниковать и отступить. Сам Бэйлен не отступает никогда."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.ARMOR, value=10.0, is_percentage=False
        ),
        "lore_description": (
            "Легенда Ордена рыцарей, повел свой полк в самоубийственную атаку в Ничьи земли "
            "и потерял всех. Выжил, но разум сломан виной. Поклялся не снимать латы, пока не "
            "искупит вину кровью, и ищет смерти, которая все не приходит."
        ),
    },
}
