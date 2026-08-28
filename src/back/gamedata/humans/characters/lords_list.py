"""
Реестр легендарных правителей фракции людей.

Лор личностей - docs/factions/humans/lords.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/humans/lords/.
"""

from typing import Any

from src.back.gamedata.humans.common import HumanLordId
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.lord import LordStrategicBias

_RACE = FactionRace.HUMANS
_PROMPTS = "unique_personalities.humans.lords"

LORDS_LIST: dict[str, dict[str, Any]] = {
    HumanLordId.BENEDICT_STRAUSS.value: {
        "id": HumanLordId.BENEDICT_STRAUSS.value,
        "race": _RACE,
        "name": "Бенедикт Штраусс",
        "title": "Верховный канцлер",
        "archetype": "Верховный канцлер",
        "prompt_ref": f"{_PROMPTS}.Benedict_Strauss",
        "trait_ids": ["bureaucrat", "greedy", "paranoid"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.8,  # Поборы на уголь и провизию - его любимый инструмент
            military_building_priority=-0.4,
            diplomatic_aggression=0.3,
            bribery_susceptibility=0.6,  # С соседями говорит на языке золота
        ),
        "lore_description": (
            "Правитель Альт-Атласа. Никогда не держал в руках мушкет, но одним росчерком "
            "пера отправляет на смерть целые полки: люди для него - строки в расходных книгах, "
            "а выживание Империи - бухгалтерская задача. Панически боится мутаций."
        ),
    },
    HumanLordId.WOLFRAM_KRANZ.value: {
        "id": HumanLordId.WOLFRAM_KRANZ.value,
        "race": _RACE,
        "name": "Вольфрам Кранц",
        "title": "Обер-мастер",
        "archetype": "Технократ-утилитарист",
        "prompt_ref": f"{_PROMPTS}.Wolfram_Kranz",
        "trait_ids": ["pragmatist", "cynic", "perfectionist"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.5,
            military_building_priority=0.8,  # Пушки и броня без остановки
            diplomatic_aggression=0.5,
            bribery_susceptibility=0.4,
        ),
        "lore_description": (
            "Властитель Железной пади, пропахший машинным маслом и расплавленным чугуном. "
            "Считает мораль и религию помехой производственному процессу, а покалеченных "
            "рабочих без сантиментов отправляет на переплавку шлака."
        ),
    },
    HumanLordId.EMERICH_FALK.value: {
        "id": HumanLordId.EMERICH_FALK.value,
        "race": _RACE,
        "name": "Эмерих Фальк",
        "title": "Архиепископ",
        "archetype": "Архиепископ",
        "prompt_ref": f"{_PROMPTS}.Emerich_Falk",
        "trait_ids": ["inquisitor", "sadist", "fatalist"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.3,
            military_building_priority=0.4,
            diplomatic_aggression=0.8,  # Ересь не обсуждают, ересь выжигают
            bribery_susceptibility=0.1,
        ),
        "lore_description": (
            "Владыка Предела святого Малахии. Говорит тихим голосом уставшего отца и "
            "искренне любит человечество - именно поэтому считает своим долгом очищать его "
            "через боль. Батальоны Кающихся грешников он отправляет на смерть со слезами."
        ),
    },
    HumanLordId.KASPAR_DRAKE.value: {
        "id": HumanLordId.KASPAR_DRAKE.value,
        "race": _RACE,
        "name": "Каспар Драке",
        "title": "Комендант",
        "archetype": "Окопный мясник",
        "prompt_ref": f"{_PROMPTS}.Kaspar_Drake",
        "trait_ids": ["cynic", "fatalist", "gladiator"],
        "bias": LordStrategicBias(
            tax_rate_bias=-0.2,  # С пограничной нищеты нечего брать
            military_building_priority=0.9,
            diplomatic_aggression=0.6,
            bribery_susceptibility=0.2,
        ),
        "lore_description": (
            "Ветеран пятидесяти осад, комендант Врат висельников. Командует штрафными "
            "батальонами на самой границе Ничьей земли, живет в бункере в толще стены и судит "
            "солдат взмахом руки в сторону виселиц. Отступать ему некуда."
        ),
    },
}
