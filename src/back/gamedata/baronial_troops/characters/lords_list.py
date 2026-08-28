"""
Реестр легендарных правителей баронств.

Баронства - неиграбельная сила Ничьей земли: их лордами управляет
нейтральная языковая модель, игрок за них не играет.

Лор личностей - docs/factions/baronial_troops/lords.md, их системные промпты -
l03_infrastructure/llm/prompt/unique_personalities/baronial_troops/lords/.
"""

from typing import Any

from src.back.gamedata.baronial_troops.common import BaronialLordId
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.lord import LordStrategicBias

_RACE = FactionRace.BARONIAL_TROOPS
_PROMPTS = "unique_personalities.baronial_troops.lords"

LORDS_LIST: dict[str, dict[str, Any]] = {
    BaronialLordId.ARCHDUKE_WALTER.value: {
        "id": BaronialLordId.ARCHDUKE_WALTER.value,
        "race": _RACE,
        "name": "Вальтер",
        "title": "Эрцгерцог",
        "archetype": "Владыка пошлин",
        "prompt_ref": f"{_PROMPTS}.Archduke_Walter",
        "trait_ids": ["greedy", "bureaucrat", "paranoid"],
        "bias": LordStrategicBias(
            tax_rate_bias=1.0,
            military_building_priority=0.2,
            diplomatic_aggression=0.4,
            bribery_susceptibility=0.8,  # Все решает предоплата за десять тактов вперед
        ),
        "lore_description": (
            "Правитель Баронства Медных врат, перекрывающего единственный безопасный тракт "
            "сквозь Ущелье Скорбящих. Маниакально проверяет подлинность монет. Для него есть "
            "только те, кто оплатил пошлину, и те, кого нужно расстрелять за неуплату."
        ),
    },
    BaronialLordId.LADY_ISOLDE.value: {
        "id": BaronialLordId.LADY_ISOLDE.value,
        "race": _RACE,
        "name": "Изольда",
        "title": "Леди",
        "archetype": "Ростовщица",
        "prompt_ref": f"{_PROMPTS}.Lady_Isolde",
        "trait_ids": ["pragmatist", "greedy", "aristocrat"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.7,
            military_building_priority=-0.2,
            diplomatic_aggression=0.2,
            bribery_susceptibility=1.0,
        ),
        "lore_description": (
            "Глава Синдиката Ржавой короны - крупнейшей контрабандной сети Ничьей земли. "
            "Торгует со всеми враждующими сторонами разом: имперским зерном с орками, "
            "эльфийским вином с инквизиторами. Война для нее - рост цен на бинты и гробы."
        ),
    },
    BaronialLordId.CORNELIUS_HOOK.value: {
        "id": BaronialLordId.CORNELIUS_HOOK.value,
        "race": _RACE,
        "name": "Корнелий Крюк",
        "title": "Барон",
        "archetype": "Псарник-садист",
        "prompt_ref": f"{_PROMPTS}.Cornelius_Hook",
        "trait_ids": ["sadist", "gladiator", "vengeful"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.5,
            military_building_priority=0.9,
            diplomatic_aggression=0.9,
            bribery_susceptibility=0.5,  # Признает силу и звонкую монету
        ),
        "lore_description": (
            "Правитель Баронства Кровавого гребня на границе с землями зеленокожих. Перенял "
            "у дикарей их методы: замок окружен ямами с кольями, где на цепях сидят боевые "
            "огры и бронированные волкодавы. Оценивает послов по минутам на своей арене."
        ),
    },
    BaronialLordId.RODERICK_VON_DRAKEN.value: {
        "id": BaronialLordId.RODERICK_VON_DRAKEN.value,
        "race": _RACE,
        "name": "Родерик фон Дракен",
        "title": "Маркграф",
        "archetype": "Тюремный монополист",
        "prompt_ref": f"{_PROMPTS}.Roderick_von_Draken",
        "trait_ids": ["bureaucrat", "greedy", "cynic"],
        "bias": LordStrategicBias(
            tax_rate_bias=0.9,
            military_building_priority=0.3,
            diplomatic_aggression=0.5,
            bribery_susceptibility=0.7,
        ),
        "lore_description": (
            "Властитель Маркграфства Черных топей, превративший феодальный суд в "
            "индустриальный конвейер. По его «Кодексу топей» вход на болота облагается налогом "
            "на дыхание, а побежденные отправляются в Долговые тюрьмы до уплаты выкупа."
        ),
    },
}
