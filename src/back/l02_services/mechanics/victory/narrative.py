"""
Формулировки финала партии.

Экрану окончания игры и летописцу нужна не константа "economic", а фраза,
которой заканчивают хронику. Тексты собраны здесь, отдельно от проверки
условий: правила победы и слова о ней меняются по разным поводам.

Языковая модель сюда не ходит - это гарантированная подпись под финалом,
которая будет на экране даже при выключенном летописце.
"""

from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.world.constants import VictoryType
from src.back.l01_domain.world.models.victory import VictoryProgress

# ==================================================================
# ПОБЕДА ИГРОКА
# ==================================================================

_PLAYER_VICTORY_TEMPLATES: dict[VictoryType, str] = {
    VictoryType.DOMINATION: (
        "Территориальное господство. Последняя вражеская цитадель догорела, и "
        "над Ничьей землей не осталось знамени, кроме знамени фракции «{faction}»."
    ),
    VictoryType.ECONOMIC: (
        "Экономическое процветание. Казна фракции «{faction}» приняла "
        "{gold:.0f} золота, {material:.0f} материалов и {food:.0f} провизии: "
        "амбары переполнены, а мастерские работают без остановки."
    ),
    VictoryType.EXPANSION: (
        "Основание страны. Фракция «{faction}» довела до {level}-го уровня "
        "{towns} пограничных городов, и разрозненные земли впервые после "
        "Катаклизма стали единым государством."
    ),
}

# ==================================================================
# ПОБЕДА СОПЕРНИКА
# ==================================================================

_RIVAL_VICTORY_TEMPLATES: dict[VictoryType, str] = {
    VictoryType.DOMINATION: (
        "Фракция «{faction}» дожгла цитадели всех соперников и осталась на "
        "карте одна. Партия проиграна."
    ),
    VictoryType.ECONOMIC: (
        "Фракция «{faction}» скопила богатство, за которым уже не угнаться: "
        "ее казна взяла все три порога процветания. Партия проиграна."
    ),
    VictoryType.EXPANSION: (
        "Фракция «{faction}» подняла {towns} города до {level}-го уровня и "
        "объявила о рождении своей державы. Партия проиграна."
    ),
}


def describe_player_victory(
    victory_type: VictoryType, faction: Faction, progress: VictoryProgress
) -> str:
    """
    Причина победы игрока - то, что читается на экране финала крупным шрифтом.
    """
    return _PLAYER_VICTORY_TEMPLATES[victory_type].format(
        faction=faction.name,
        gold=progress.current_gold,
        material=progress.current_material,
        food=progress.current_food,
        towns=progress.max_level_towns_count,
        level=progress.required_town_level,
    )


def describe_rival_victory(
    victory_type: VictoryType, faction: Faction, progress: VictoryProgress
) -> str:
    """
    Причина поражения, когда цель первым взял соперник, а не игрок.
    """
    return _RIVAL_VICTORY_TEMPLATES[victory_type].format(
        faction=faction.name,
        towns=progress.max_level_towns_count,
        level=progress.required_town_level,
    )


# ==================================================================
# ПОРАЖЕНИЕ ИГРОКА
# ==================================================================


def describe_defeat(faction: Faction) -> str:
    """
    Причина выбывания игрока.

    Два конца выглядят по-разному: сожженная цитадель - это штурм, а
    полное разорение - медленная смерть от голода и безденежья, и на экране
    финала они не должны читаться одинаково.
    """
    if faction.headquarters.is_destroyed:
        return (
            f"Цитадель «{faction.headquarters.name}» пала под штурмом. "
            f"Фракция «{faction.name}» перестала существовать."
        )
    return (
        f"У фракции «{faction.name}» не осталось ни войск, ни поселений, ни "
        "производств, ни казны: держава рассыпалась сама собой."
    )
