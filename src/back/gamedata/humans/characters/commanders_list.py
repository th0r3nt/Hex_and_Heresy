"""
Реестр легендарных полководцев фракции людей.

Лор личностей - docs/factions/humans/commanders.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/humans/commanders/.
"""

from typing import Any

from src.back.gamedata.humans.common import HumanCommanderId
from src.back.l01_domain.army.models.characters.commanders import CommanderCharacteristics
from src.back.l01_domain.common import FactionRace

_RACE = FactionRace.HUMANS
_PROMPTS = "unique_personalities.humans.commanders"

COMMANDERS_LIST: dict[str, dict[str, Any]] = {
    HumanCommanderId.GERHARD_BLOOM.value: {
        "id": HumanCommanderId.GERHARD_BLOOM.value,
        "race": _RACE,
        "name": "Герхард Блум",
        "role_title": "Интендант-полковник",
        "archetype": "Тактик на истощение",
        "prompt_ref": f"{_PROMPTS}.Gerhard_Bloom",
        "trait_ids": ["bureaucrat", "cynic", "greedy"],
        "characteristics": CommanderCharacteristics(
            authority=35,  # Речами не вдохновляет, берет страхом перед отчетностью
            tactical_acumen=70,
            resilience=45,
            cunning=60,
        ),
        "lore_description": (
            "Бывший налоговый инспектор Железной пади, переведенный в армию за махинации "
            "с углем. Высчитывает, сколько крестьян с вилами должно умереть, чтобы вражеский "
            "огр устал махать дубиной. Ведет учет потерянных алебард строже, чем учет людей."
        ),
    },
    HumanCommanderId.RENATA_FURIOUS.value: {
        "id": HumanCommanderId.RENATA_FURIOUS.value,
        "race": _RACE,
        "name": "Рената Неистовая",
        "role_title": "Капитан авангарда",
        "archetype": "Фанатик без обратного пути",
        "prompt_ref": f"{_PROMPTS}.Renata_Furious",
        "trait_ids": ["inquisitor", "fatalist", "vengeful"],
        "characteristics": CommanderCharacteristics(
            authority=75,
            tactical_acumen=40,
            resilience=80,
            cunning=25,
        ),
        "lore_description": (
            "Выжила в резне на границе Ничьей земли, спрятавшись под телами сестер, и "
            "считает, что украла чужую мученическую смерть. Ее солдаты сражаются не за победу, "
            "а из животного страха: «Империи не нужны те, кто возвращается»."
        ),
    },
    HumanCommanderId.JURGEN_SCHWARTZ.value: {
        "id": HumanCommanderId.JURGEN_SCHWARTZ.value,
        "race": _RACE,
        "name": "Юрген Шварц",
        "role_title": "Магистр артиллерии",
        "archetype": "Пороховой стратег",
        "prompt_ref": f"{_PROMPTS}.Jurgen_Schwartz",
        "trait_ids": ["perfectionist", "pragmatist"],
        "characteristics": CommanderCharacteristics(
            authority=50,
            tactical_acumen=85,
            resilience=40,
            cunning=45,
        ),
        "lore_description": (
            "Выпускник артиллерийской школы Железной пади, наполовину оглохший от сотен "
            "залпов. Воспринимает войну как задачу с переменными дистанции, плотности огня и "
            "расхода пороха: его шеренги выкашивают врага задолго до рукопашной."
        ),
    },
}
