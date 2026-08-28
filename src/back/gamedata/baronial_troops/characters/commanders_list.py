"""
Реестр легендарных полководцев баронств.

Лор личностей - docs/factions/baronial_troops/commanders.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/baronial_troops/commanders/.
"""

from typing import Any

from src.back.gamedata.baronial_troops.common import BaronialCommanderId
from src.back.l01_domain.army.models.characters.commanders import CommanderCharacteristics
from src.back.l01_domain.common import FactionRace

_RACE = FactionRace.BARONIAL_TROOPS
_PROMPTS = "unique_personalities.baronial_troops.commanders"

COMMANDERS_LIST: dict[str, dict[str, Any]] = {
    BaronialCommanderId.OLGERD.value: {
        "id": BaronialCommanderId.OLGERD.value,
        "race": _RACE,
        "name": "Ольгерд",
        "role_title": "Капитан павезников",
        "archetype": "Капитан павезников",
        "prompt_ref": f"{_PROMPTS}.Olgerd",
        "trait_ids": ["perfectionist", "bureaucrat", "pragmatist"],
        "characteristics": CommanderCharacteristics(
            authority=65,
            tactical_acumen=70,
            resilience=90,
            cunning=30,
        ),
        "lore_description": (
            "Бывший имперский ветеран, доведший позиционную оборону до абсолюта. Его "
            "доктрина - «держать строй и не делать лишних шагов»: стоящие в обороне роты "
            "удваивают броню и поглощают первые залпы ростовыми щитами."
        ),
    },
    BaronialCommanderId.JURGEN.value: {
        "id": BaronialCommanderId.JURGEN.value,
        "race": _RACE,
        "name": "Юрген",
        "role_title": "Старший палач",
        "archetype": "Палач",
        "prompt_ref": f"{_PROMPTS}.Jurgen",
        "trait_ids": ["sadist", "inquisitor"],
        "characteristics": CommanderCharacteristics(
            authority=90,  # Дисциплина держится на первобытном ужасе
            tactical_acumen=30,
            resilience=70,
            cunning=25,
        ),
        "lore_description": (
            "Двухметровый громила в железной маске и пропитанном кровью фартуке. Не обучает "
            "солдат тактике, а управляет ими через ужас: колеблющемуся крестьянину он "
            "показательно отрубает голову, мгновенно восстанавливая строй."
        ),
    },
    BaronialCommanderId.SIR_DIETRICH.value: {
        "id": BaronialCommanderId.SIR_DIETRICH.value,
        "race": _RACE,
        "name": "Сэр Дитрих",
        "role_title": "Капитан тяжелой конницы",
        "archetype": "Рыцарь-наемник",
        "prompt_ref": f"{_PROMPTS}.Sir_Dietrich",
        "trait_ids": ["cynic", "greedy", "aristocrat"],
        "characteristics": CommanderCharacteristics(
            authority=55,
            tactical_acumen=65,
            resilience=45,
            cunning=60,
        ),
        "lore_description": (
            "Изгнанный из имперского ордена рыцарь, сбивший зубилом гербы со своих лат. "
            "Требует тройное жалование и не верит в рыцарскую честь, но его кавалерийский "
            "натиск за один такт сминает строй эльфийских стражей."
        ),
    },
}
