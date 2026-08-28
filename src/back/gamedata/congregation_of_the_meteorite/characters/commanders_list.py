"""
Реестр легендарных полководцев Паствы метеорита.

Лор личностей - docs/factions/congregation_of_the_meteorite/commanders.md, их системные
промпты - l03_infrastructure/llm/prompt/unique_personalities/congregation_of_the_meteorite/commanders/.
"""

from typing import Any

from src.back.gamedata.congregation_of_the_meteorite.common import CongregationCommanderId
from src.back.l01_domain.army.models.characters.commanders import CommanderCharacteristics
from src.back.l01_domain.common import FactionRace

_RACE = FactionRace.CONGREGATION_OF_THE_METEORITE
_PROMPTS = "unique_personalities.congregation_of_the_meteorite.commanders"

COMMANDERS_LIST: dict[str, dict[str, Any]] = {
    CongregationCommanderId.NEKRAS.value: {
        "id": CongregationCommanderId.NEKRAS.value,
        "race": _RACE,
        "name": "Некрас",
        "role_title": "Погонщик мертвецов",
        "archetype": "Погонщик мертвецов",
        "prompt_ref": f"{_PROMPTS}.Nekras",
        "trait_ids": ["necrosis", "cynic", "pragmatist"],
        "characteristics": CommanderCharacteristics(
            authority=75,  # Мертвым не нужна вера в командира, им нужен импульс
            tactical_acumen=55,
            resilience=60,
            cunning=40,
        ),
        "lore_description": (
            "Бывший имперский полевой хирург, увитый трубками для перекачки спинномозговой "
            "жидкости и резонитовой взвеси. Держится позади строя, прошивая мертвые тела "
            "гальваническими импульсами: его орды идут на копья без капли страха."
        ),
    },
    CongregationCommanderId.VARG.value: {
        "id": CongregationCommanderId.VARG.value,
        "race": _RACE,
        "name": "Варг",
        "role_title": "Вожак стаи",
        "archetype": "Хищник",
        "prompt_ref": f"{_PROMPTS}.Varg",
        "trait_ids": ["lycanthropy", "vengeful", "sadist"],
        "characteristics": CommanderCharacteristics(
            authority=60,
            tactical_acumen=50,
            resilience=70,
            cunning=85,  # Обходы с флангов и ночные засады
        ),
        "lore_description": (
            "Командир оборотней и мутировавших зверей с терминальным Изъяном ликантропии. "
            "В серые часы - угрюмый человек в рваных шкурах, в неоновые - трехметровый вожак "
            "стаи. Его отряды рвут раненых и бегущих, но требуют гор сырого мяса."
        ),
    },
    CongregationCommanderId.NAMELESS_KNIGHT.value: {
        "id": CongregationCommanderId.NAMELESS_KNIGHT.value,
        "race": _RACE,
        "name": "Безымянный рыцарь",
        "role_title": "Офицер Бессмертных всадников",
        "archetype": "Призрачный авангард",
        "prompt_ref": f"{_PROMPTS}.Nameless_Knight",
        "trait_ids": ["decay", "fatalist", "aristocrat"],
        "characteristics": CommanderCharacteristics(
            authority=70,
            tactical_acumen=60,
            resilience=95,
            cunning=45,
        ),
        "lore_description": (
            "Обезглавленный труп древнего паладина, чья душа зациклилась на силовом поле "
            "Изъяна распада. Левитирует во главе безмолвной кавалерии, игнорируя болота и "
            "реки. Если его армия гибнет, он материализуется в склепе базы через два такта."
        ),
    },
}
