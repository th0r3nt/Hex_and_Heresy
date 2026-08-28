"""
Реестр легендарных героев фракции эльфов.

Лор личностей - docs/factions/elfs/heroes.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/elfs/heroes/.
"""

from typing import Any

from src.back.gamedata.elfs.common import ElfsHeroId
from src.back.l01_domain.common import FactionRace, MechanicalModifier, StatName

_RACE = FactionRace.ELFS
_PROMPTS = "unique_personalities.elfs.heroes"

HEROES_LIST: dict[str, dict[str, Any]] = {
    ElfsHeroId.ILLITHIAN.value: {
        "id": ElfsHeroId.ILLITHIAN.value,
        "race": _RACE,
        "name": "Иллитиан",
        "archetype": "Живой монолит",
        "prompt_ref": f"{_PROMPTS}.Illithian",
        "trait_ids": ["monolith", "fatalist", "aristocrat"],
        "max_hp": 300.0,
        "special_rule": (
            "Не чувствует боли: Иллитиан игнорирует штрафы от ранений и не может быть "
            "принужден к отступлению эффектами страха."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.ARMOR, value=12.0, is_percentage=False
        ),
        "lore_description": (
            "Ему более трех тысяч лет, и тело не выдержало симбиоза с резонитом: половина "
            "плоти, включая левую руку и часть лица, стала светящимся изумрудным кристаллом. "
            "Его меч - продолжение хрустальной руки. Ищет достойную смерть в бою."
        ),
    },
    ElfsHeroId.ERINNIEL.value: {
        "id": ElfsHeroId.ERINNIEL.value,
        "race": _RACE,
        "name": "Эринниэль",
        "archetype": "Манипулятор",
        "prompt_ref": f"{_PROMPTS}.Erinniel",
        "trait_ids": ["megalomaniac", "resonance", "perfectionist"],
        "max_hp": 130.0,
        "special_rule": (
            "Убеждение пространства: раз в бой Эринниэль вычеркивает один вражеский отряд "
            "с занимаемой им клетки, отбрасывая его назад по строю."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.INITIATIVE, value=4.0, is_percentage=False
        ),
        "lore_description": (
            "Живет в парящих храмах и смотрит на мир как на плохо написанный черновик. "
            "Виртуозно владеет информационным кодом резонита: не стреляет огнем, а убеждает "
            "пространство, что врага здесь быть не должно. Левитирует, чтобы не касаться земли."
        ),
    },
    ElfsHeroId.FENARIL.value: {
        "id": ElfsHeroId.FENARIL.value,
        "race": _RACE,
        "name": "Фэнарил",
        "archetype": "Одичавший",
        "prompt_ref": f"{_PROMPTS}.Fenaril",
        "trait_ids": ["lycanthropy", "vengeful", "resonance"],
        "max_hp": 200.0,
        "special_rule": (
            "Кислотная кровь: любой отряд, добивший Фэнарила в ближнем бою, получает урон "
            "от разъедающих брызг. Его отравленные шипы игнорируют часть брони."
        ),
        "trigger_modifier": MechanicalModifier(
            stat_name=StatName.RANGED_ACCURACY, value=0.25, is_percentage=True
        ),
        "lore_description": (
            "Тысячелетиями выживал в глубочайших кратерах Прародителя и одичал. Кровь стала "
            "едкой кислотой, лицо скрыто маской из черепа мутанта. Стреляет отравленными "
            "шипами, и его всегда сопровождает стая искаженных мутацией гончих."
        ),
    },
}
