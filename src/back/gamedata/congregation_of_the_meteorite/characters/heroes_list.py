"""
Реестр легендарных героев Паствы метеорита.

Лор личностей - docs/factions/congregation_of_the_meteorite/heroes.md, их системные
промпты - l03_infrastructure/llm/prompt/unique_personalities/congregation_of_the_meteorite/heroes/.
"""

from typing import Any

from src.back.gamedata.congregation_of_the_meteorite.common import CongregationHeroId
from src.back.l01_domain.common import FactionRace, MechanicalModifier, StatName

_RACE = FactionRace.CONGREGATION_OF_THE_METEORITE
_PROMPTS = "unique_personalities.congregation_of_the_meteorite.heroes"

HEROES_LIST: dict[str, dict[str, Any]] = {
    CongregationHeroId.ILAI.value: {
        "id": CongregationHeroId.ILAI.value,
        "race": _RACE,
        "name": "Илай",
        "archetype": "Видящий смерть",
        "prompt_ref": f"{_PROMPTS}.Ilai",
        "trait_ids": ["resonance", "fatalist", "sadist"],
        "max_hp": 160.0,
        "special_rule": (
            "Все уже мертвы: Илай заранее видит, кто падет, и его атаки бьют точно по тем "
            "отрядам врага, что и так на грани - добивая раненых с удвоенной эффективностью."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.INITIATIVE, value=5.0, is_percentage=False
        ),
        "lore_description": (
            "Талантливый полевой хирург Империи, экспериментировавший с микродозами "
            "первичной взвеси ради регенерации. Резонит сцепился с информационным полем в "
            "обратном порядке: теперь он видит не живых людей, а их будущие трупы."
        ),
    },
    CongregationHeroId.MALAKAI.value: {
        "id": CongregationHeroId.MALAKAI.value,
        "race": _RACE,
        "name": "Малакай",
        "archetype": "Искаженный священник",
        "prompt_ref": f"{_PROMPTS}.Malakai",
        "trait_ids": ["inquisitor", "megalomaniac", "chaos"],
        "max_hp": 200.0,
        "special_rule": (
            "Видит души: слепой Малакай не подвержен иллюзиям, дыму и маскировке и находит "
            "вражеских героев в любом строю, где бы те ни прятались."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.MORALE, value=15.0, is_percentage=False
        ),
        "lore_description": (
            "Бывший имперский Инквизитор: допрашивая чернокнижника, вдохнул дозу Первичной "
            "взвеси и в коме «поговорил» с ядром Прародителя. Проснувшись, убил коллег и сжег "
            "часовню. Залил глаза свинцом, но видит души как электромагнитные поля."
        ),
    },
}
