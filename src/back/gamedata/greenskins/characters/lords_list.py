"""
Реестр легендарных вождей фракции зеленокожих.

Лор личностей - docs/factions/greenskins/lords.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/greenskins/lords/.
"""

from typing import Any

from src.back.gamedata.greenskins.common import GreenskinsLordId
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.lord import LordStrategicBias

_RACE = FactionRace.GREENSKINS
_PROMPTS = "unique_personalities.greenskins.lords"

LORDS_LIST: dict[str, dict[str, Any]] = {
    GreenskinsLordId.GURG_SPOREBEARER.value: {
        "id": GreenskinsLordId.GURG_SPOREBEARER.value,
        "race": _RACE,
        "name": "Гург Спороносец",
        "title": "Вождь-жрец",
        "archetype": "Жрец мицелия",
        "prompt_ref": f"{_PROMPTS}.Gurg_Sporebearer",
        "trait_ids": ["megalomaniac", "hyperplasia", "sadist"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.2,
            military_building_priority=0.7,
            diplomatic_aggression=0.9,  # Империя для него - болезнь, а не собеседник
            bribery_susceptibility=0.0,
        ),
        "lore_description": (
            "Трехметровый гигант, чья кожа покрыта слоем ядовитого мха. Верит в «Чистоту "
            "гнили»: его орда не захватывает территории, а засеивает их, закапывая пленных "
            "заживо, чтобы на них росли новые орки. Ждет цветения Прародителя."
        ),
    },
    GreenskinsLordId.BARON_KHMYR.value: {
        "id": GreenskinsLordId.BARON_KHMYR.value,
        "race": _RACE,
        "name": "Хмырь",
        "title": "Барыга-барон",
        "archetype": "Жадный рэкетир",
        "prompt_ref": f"{_PROMPTS}.Baron_Khmyr",
        "trait_ids": ["greedy", "cynic", "pragmatist"],
        "bias": LordStrategicBias(
            tax_rate_bias=1.0,
            military_building_priority=-0.3,
            diplomatic_aggression=0.3,  # Пока платят - улыбается
            bribery_susceptibility=0.9,
        ),
        "lore_description": (
            "Редчайший случай: во главе союза племен стоит не огромный орк, а хитрый старый "
            "гоблин. Держит власть богатством и свитой подкупленных огров, контролирует "
            "воровские туннели и свалки. Ударит в тыл, как только у нанимателя кончится золото."
        ),
    },
    GreenskinsLordId.NAGROK_STEEL_EATER.value: {
        "id": GreenskinsLordId.NAGROK_STEEL_EATER.value,
        "race": _RACE,
        "name": "Нагрок Жрущий Сталь",
        "title": "Вождь орды",
        "archetype": "Живой таран",
        "prompt_ref": f"{_PROMPTS}.Nagrok_Steel_Eater",
        "trait_ids": ["hyperplasia", "megalomaniac", "vengeful"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.0,  # Кочующая орда не собирает дань, она жрет металл
            military_building_priority=1.0,
            diplomatic_aggression=1.0,
            bribery_susceptibility=0.0,
        ),
        "lore_description": (
            "Вождь мутировавших орков-ассимиляторов. Облучение резонитом лишило его плоть "
            "способности отвергать чужеродные материалы: он впаял в кости бронелисты, шестерни "
            "и штыки. Ведет орду от одного поля брани к другому, чтобы пожирать металл."
        ),
    },
}
