"""
Реестр легендарных иерархов Паствы метеорита.

Лор личностей - docs/factions/congregation_of_the_meteorite/lords.md, их системные
промпты - l03_infrastructure/llm/prompt/unique_personalities/congregation_of_the_meteorite/lords/.
"""

from typing import Any

from src.back.gamedata.congregation_of_the_meteorite.common import CongregationLordId
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.lord import LordStrategicBias

_RACE = FactionRace.CONGREGATION_OF_THE_METEORITE
_PROMPTS = "unique_personalities.congregation_of_the_meteorite.lords"

LORDS_LIST: dict[str, dict[str, Any]] = {
    CongregationLordId.MORDIUS.value: {
        "id": CongregationLordId.MORDIUS.value,
        "race": _RACE,
        "name": "Мордиус",
        "title": "Архиерей плоти",
        "archetype": "Архиерей плоти",
        "prompt_ref": f"{_PROMPTS}.Mordius",
        "trait_ids": ["perfectionist", "necrosis", "pragmatist"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.4,
            military_building_priority=0.6,
            diplomatic_aggression=0.6,
            bribery_susceptibility=0.6,  # Охотно торгует темным оружием за «сырье»
        ),
        "lore_description": (
            "Главный анатомический мастер Паствы, превративший Костяные ямы в биоинженерную "
            "мануфактуру. Относится к телам смертных как к нерационально спроектированному "
            "сырью. Пальцы заменены скальпелями и иглами из метеоритного железа."
        ),
    },
    CongregationLordId.VLASTA.value: {
        "id": CongregationLordId.VLASTA.value,
        "race": _RACE,
        "name": "Власта",
        "title": "Графиня",
        "archetype": "Графиня-вампир",
        "prompt_ref": f"{_PROMPTS}.Vlasta",
        "trait_ids": ["desiccation", "aristocrat", "hedonist"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.8,  # Кровяная дань собирается так же методично, как налог
            military_building_priority=0.3,
            diplomatic_aggression=0.4,
            bribery_susceptibility=0.7,
        ),
        "lore_description": (
            "Бывшая имперская аристократка, чей род первым поразил Изъян иссушения. "
            "Выстроила в катакомбах декадентский двор, где плазма разных рас дегустируется "
            "как вино. Опутывает независимых баронов «пактами защиты» и кровяной данью."
        ),
    },
    CongregationLordId.XAPHAN.value: {
        "id": CongregationLordId.XAPHAN.value,
        "race": _RACE,
        "name": "Ксафан",
        "title": "Глашатай Бездны",
        "archetype": "Глашатай бездны",
        "prompt_ref": f"{_PROMPTS}.Xaphan",
        "trait_ids": ["chaos", "megalomaniac", "fatalist"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.0,  # Презирает накопительство: материя - проклятие
            military_building_priority=0.8,
            diplomatic_aggression=1.0,
            bribery_susceptibility=0.0,
        ),
        "lore_description": (
            "Верховный сектант Врат Бездны: обугленный кокон, сквозь трещины которого "
            "вырывается плазма Изъяна хаоса. Готов пожертвовать половиной базы и тысячами "
            "культистов ради ритуала призыва, превращая войну в акт космической аннигиляции."
        ),
    },
}
