"""
Реестр легендарных владык фракции эльфов.

Лор личностей - docs/factions/elfs/lords.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/elfs/lords/.
"""

from typing import Any

from src.back.gamedata.elfs.common import ElfsLordId
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.lord import LordStrategicBias

_RACE = FactionRace.ELFS
_PROMPTS = "unique_personalities.elfs.lords"

LORDS_LIST: dict[str, dict[str, Any]] = {
    ElfsLordId.LIANDRIS.value: {
        "id": ElfsLordId.LIANDRIS.value,
        "race": _RACE,
        "name": "Лиандрис",
        "title": "Владыка Эфирного Зенита",
        "archetype": "Стеклянный демиург",
        "prompt_ref": f"{_PROMPTS}.Liandris",
        "trait_ids": ["megalomaniac", "perfectionist", "monolith"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.4,
            military_building_priority=0.3,
            diplomatic_aggression=0.7,
            bribery_susceptibility=0.0,  # Золото для него - грязный металл
        ),
        "lore_description": (
            "Не касался поверхности земли более двух тысяч лет. Воспринимает планету как "
            "черновик, который нужно стереть и переписать в чистые геометрические формы. "
            "Требует передавать послания на резонитовых пластинах, а не на «останках деревьев»."
        ),
    },
    ElfsLordId.NAERIL.value: {
        "id": ElfsLordId.NAERIL.value,
        "race": _RACE,
        "name": "Наэриль",
        "title": "Владычица Архивов",
        "archetype": "Утратившая время",
        "prompt_ref": f"{_PROMPTS}.Naeril",
        "trait_ids": ["resonance", "fatalist", "aristocrat"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.0,
            military_building_priority=0.0,
            diplomatic_aggression=0.4,  # Симпатии меняются вместе с ее веком
            bribery_susceptibility=0.3,
        ),
        "lore_description": (
            "Тысячелетний симбиоз с резонитом заставил ее мозг непрерывно считывать "
            "информационное поле планеты - и стер ощущение хронологии. На аудиенции может "
            "потребовать у посла вернуть долг за битву трехвековой давности."
        ),
    },
    ElfsLordId.VALORIS.value: {
        "id": ElfsLordId.VALORIS.value,
        "race": _RACE,
        "name": "Валорис",
        "title": "Властитель Белого шума",
        "archetype": "Абсолютный изоляционист",
        "prompt_ref": f"{_PROMPTS}.Valoris",
        "trait_ids": ["paranoid", "perfectionist", "megalomaniac"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.6,  # Наемников, выжигающих округу, надо чем-то оплачивать
            military_building_priority=0.5,
            diplomatic_aggression=0.6,
            bribery_susceptibility=0.2,
        ),
        "lore_description": (
            "Убежден, что любой звук громче звона хрусталя ускоряет энтропию. В его владениях "
            "запрещены человеческая речь и порох под страхом расщепления голосовых связок. "
            "Платит наемникам за одно: выжечь вокруг границ зону абсолютной тишины."
        ),
    },
}
