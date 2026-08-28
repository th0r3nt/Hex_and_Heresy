"""
Реестр легендарных полководцев фракции зеленокожих.

Лор личностей - docs/factions/greenskins/commanders.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/greenskins/commanders/.
"""

from typing import Any

from src.back.gamedata.greenskins.common import GreenskinsCommanderId
from src.back.l01_domain.army.models.characters.commanders import CommanderCharacteristics
from src.back.l01_domain.common import FactionRace

_RACE = FactionRace.GREENSKINS
_PROMPTS = "unique_personalities.greenskins.commanders"

COMMANDERS_LIST: dict[str, dict[str, Any]] = {
    GreenskinsCommanderId.GOROG_THE_SILENT.value: {
        "id": GreenskinsCommanderId.GOROG_THE_SILENT.value,
        "race": _RACE,
        "name": "Горог Тихий",
        "role_title": "Вожак авангарда",
        "archetype": "Мясник авангарда",
        "prompt_ref": f"{_PROMPTS}.Gorog_the_Silent",
        "trait_ids": ["fatalist", "sadist", "monolith"],
        "characteristics": CommanderCharacteristics(
            authority=80,  # Не орет, просто молча рубит головы отстающим
            tactical_acumen=45,
            resilience=85,
            cunning=30,
        ),
        "lore_description": (
            "Имперское ядро снесло ему половину черепа, и шаманы вбили в дыру медную "
            "пластину. Это спасло жизнь, но убило орочью ярость. Горог двигается в жуткой "
            "тишине, и его армия идет в бой без кличей - только хруст костей."
        ),
    },
    GreenskinsCommanderId.JIGS.value: {
        "id": GreenskinsCommanderId.JIGS.value,
        "race": _RACE,
        "name": "Джигс",
        "role_title": "Старший инженер орды",
        "archetype": "Осадный безумец",
        "prompt_ref": f"{_PROMPTS}.Jigs",
        "trait_ids": ["megalomaniac", "chaos"],
        "characteristics": CommanderCharacteristics(
            authority=40,
            tactical_acumen=65,
            resilience=35,
            cunning=55,
        ),
        "lore_description": (
            "Инженер ржавых фур, катапульт и ворованных имперских мортир. Убежден, что любую "
            "стену можно превратить в щепки, если засыпать двойную порцию пороха и горсть "
            "ржавых гвоздей. Платой служат осечки и аварии в обозе."
        ),
    },
    GreenskinsCommanderId.OVERSEER_KROK.value: {
        "id": GreenskinsCommanderId.OVERSEER_KROK.value,
        "race": _RACE,
        "name": "Надсмотрщик Крок",
        "role_title": "Погонщик зверинца",
        "archetype": "Погонщик чудовищ",
        "prompt_ref": f"{_PROMPTS}.Overseer_Krok",
        "trait_ids": ["sadist", "gladiator", "greedy"],
        "characteristics": CommanderCharacteristics(
            authority=70,
            tactical_acumen=40,
            resilience=65,
            cunning=50,
        ),
        "lore_description": (
            "Свирепый орк, увешанный цепями, крюками и бичами из воловьей кожи. Отлавливает "
            "и дрессирует пещерных огров, гигантских волков и мутантов Ничьей земли, направляя "
            "их слепую ярость во вражеский строй кусками сырого мяса и ударами плети."
        ),
    },
}
