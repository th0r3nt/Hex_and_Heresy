"""
Реестр наборов инструментов (навыков) языковой модели.

Домен описывает КАЖДЫЙ навык по отдельности (l01_domain/llm/tools/definitions/).
Здесь эти навыки собираются в ИМЕНОВАННЫЕ НАБОРЫ под конкретную сцену игры:
то, что модель вправе делать во время стратегического хода державы, отличается
от того, что ей доступно в тактическом бою или на дипломатической аудиенции.

Сервисный слой просит набор по имени (`get_toolset`) и передает его в
`LLMClientProtocol.generate_with_tools`. Так на каждом шаге модель видит только
уместные инструменты и не может, например, объявить войну посреди боя.

Здесь нет исполнения вызовов: маппинг `ToolCall` на фасады сервисов - забота
`l02_services/mechanics/tools/executor.py`.
"""

from enum import Enum
from typing import Optional

from src.back.l01_domain.llm.models.tools import ToolDefinition
from src.back.l01_domain.llm.tools.definitions import (
    advisor,
    chronicler,
    diplomacy,
    game_master,
    general,
    gunsmith,
    strategic,
    tactical,
)


# ====================================================
# Наборы по категориям
# ====================================================
# Плоские списки, повторяющие разбиение доменных определений по файлам.
# Служат кирпичиками для сборки сценовых наборов ниже и точкой входа для тестов
# полноты реестра.

GENERAL_TOOLS: list[ToolDefinition] = [
    general.REPLY,
    general.STAY_SILENT,
]

STRATEGIC_TOOLS: list[ToolDefinition] = [
    strategic.ORDER_ARMY_MARCH,
    strategic.SET_TAX_RATE,
    strategic.ASSIGN_WORKER,
    strategic.UNASSIGN_WORKER,
    strategic.DISPATCH_EXPEDITION,
    strategic.FOUND_BORDER_TOWN,
    strategic.UPGRADE_BORDER_TOWN,
    strategic.CLAIM_BORDER_LAND,
    strategic.RESOLVE_BORDER_TOWN,
    strategic.STATION_SQUAD,
    strategic.UNSTATION_SQUAD,
]

TACTICAL_TOOLS: list[ToolDefinition] = [
    tactical.ORDER_SQUAD_MOVE,
    tactical.ORDER_SQUAD_HOLD,
    tactical.ORDER_SQUAD_REACTION,
]

DIPLOMACY_TOOLS: list[ToolDefinition] = [
    diplomacy.DECLARE_WAR,
    diplomacy.MAKE_PEACE,
    diplomacy.PROPOSE_TRADE,
    diplomacy.ESTABLISH_BORDERS,
    diplomacy.ESTABLISH_RIGHT_OF_PASSAGE,
    diplomacy.DEMAND_TRIBUTE,
    diplomacy.EXECUTE_AMBASSADOR,
    diplomacy.SEND_DISPATCH,
    diplomacy.SEND_AMBASSADOR,
    diplomacy.RECALL_AMBASSADOR,
    diplomacy.PAY_TRIBUTE,
]

GUNSMITH_TOOLS: list[ToolDefinition] = [
    gunsmith.DRAFT_BLUEPRINT,
    gunsmith.REJECT_BLUEPRINT,
]

GAME_MASTER_TOOLS: list[ToolDefinition] = [
    game_master.CREATE_COMMANDER,
    game_master.CREATE_HERO,
    game_master.CREATE_LORD,
    game_master.CREATE_ADVISOR,
    game_master.TRIGGER_WORLD_EVENT,
    game_master.REJECT_CREATION,
]

ADVISOR_TOOLS: list[ToolDefinition] = [
    advisor.PROPOSE_ADVISOR_ACTION,
]

CHRONICLER_TOOLS: list[ToolDefinition] = [
    chronicler.RECORD_CHRONICLE,
    chronicler.RECORD_EPITAPH,
    chronicler.RECORD_FINALE,
    chronicler.SPEAK_RUMOR,
]


# ====================================================
# Дипломатия: решения хозяина против предложений гостя
# ====================================================
# Лорд в тронном зале выносит вердикт по чужой просьбе; посол на выезде только
# торгуется и предлагает. Снаряжение и отзыв послов - инициатива своей державы
# на своем ходу, а не часть аудиенции, поэтому эти навыки уходят в
# стратегический набор.

_LORD_VERDICT_TOOLS: list[ToolDefinition] = [
    diplomacy.DECLARE_WAR,
    diplomacy.MAKE_PEACE,
    diplomacy.PROPOSE_TRADE,
    diplomacy.ESTABLISH_BORDERS,
    diplomacy.ESTABLISH_RIGHT_OF_PASSAGE,
    diplomacy.DEMAND_TRIBUTE,
    diplomacy.EXECUTE_AMBASSADOR,
]

_ENVOY_OFFER_TOOLS: list[ToolDefinition] = [
    diplomacy.PROPOSE_TRADE,
    diplomacy.ESTABLISH_BORDERS,
    diplomacy.ESTABLISH_RIGHT_OF_PASSAGE,
    diplomacy.MAKE_PEACE,
    diplomacy.DEMAND_TRIBUTE,
    diplomacy.DECLARE_WAR,
    diplomacy.PAY_TRIBUTE,
]

_FOREIGN_POLICY_TOOLS: list[ToolDefinition] = [
    diplomacy.SEND_DISPATCH,
    diplomacy.SEND_AMBASSADOR,
    diplomacy.RECALL_AMBASSADOR,
    diplomacy.PAY_TRIBUTE,
]


# ====================================================
# Именованные наборы под сцены игры
# ====================================================


class Toolset(str, Enum):
    """Сцена или роль, под которую собирается набор доступных навыков."""

    STRATEGIC_TURN = "strategic_turn"  # Стратегический ход державы на глобальной карте
    TACTICAL_BATTLE = "tactical_battle"  # Приказы отрядам в WEGO-бою
    LORD_AUDIENCE = "lord_audience"  # Лорд отвечает на депеши и послов в тронном зале
    AMBASSADOR_MISSION = "ambassador_mission"  # Посол торгуется при чужом дворе
    ADVISOR_COUNCIL = "advisor_council"  # Советник приходит к правителю с инициативой
    GUNSMITH_WORKSHOP = "gunsmith_workshop"  # Оружейник разбирает заказ на снаряжение
    GAME_MASTER_SESSION = "game_master_session"  # Мастер игры лепит сущности и события
    CHRONICLE_WRITING = "chronicle_writing"  # Летописец пишет хронику, эпитафии, слухи
    VETERAN_DIALOGUE = "veteran_dialogue"  # Именной отряд говорит с игроком


# Молчание (`stay_silent`) - законный ход: без него роль выдумывает действия,
# лишь бы вызвать хоть какой-то навык. Свободная реплика (`reply`) уместна лишь
# там, где у модели есть собеседник, - в бою и на своем ходу говорить некому.
_TOOLSETS: dict[Toolset, list[ToolDefinition]] = {
    Toolset.STRATEGIC_TURN: [
        *STRATEGIC_TOOLS,
        *_FOREIGN_POLICY_TOOLS,
        general.STAY_SILENT,
    ],
    Toolset.TACTICAL_BATTLE: [
        *TACTICAL_TOOLS,
        general.STAY_SILENT,
    ],
    Toolset.LORD_AUDIENCE: [
        *_LORD_VERDICT_TOOLS,
        *GENERAL_TOOLS,
    ],
    Toolset.AMBASSADOR_MISSION: [
        *_ENVOY_OFFER_TOOLS,
        *GENERAL_TOOLS,
    ],
    Toolset.ADVISOR_COUNCIL: [
        *ADVISOR_TOOLS,
        general.REPLY,
    ],
    Toolset.GUNSMITH_WORKSHOP: [
        *GUNSMITH_TOOLS,
        general.REPLY,
    ],
    Toolset.GAME_MASTER_SESSION: [
        *GAME_MASTER_TOOLS,
        general.REPLY,
    ],
    Toolset.CHRONICLE_WRITING: [*CHRONICLER_TOOLS],
    Toolset.VETERAN_DIALOGUE: [*GENERAL_TOOLS],
}


# ====================================================
# Индекс всех навыков по имени
# ====================================================

_CATEGORY_BUNDLES: tuple[list[ToolDefinition], ...] = (
    GENERAL_TOOLS,
    STRATEGIC_TOOLS,
    TACTICAL_TOOLS,
    DIPLOMACY_TOOLS,
    GUNSMITH_TOOLS,
    GAME_MASTER_TOOLS,
    ADVISOR_TOOLS,
    CHRONICLER_TOOLS,
)


def _index_by_name(
    bundles: tuple[list[ToolDefinition], ...],
) -> dict[str, ToolDefinition]:
    """Собирает {имя функции -> определение} без повторов, в порядке появления."""
    index: dict[str, ToolDefinition] = {}
    for bundle in bundles:
        for tool in bundle:
            index.setdefault(tool.name, tool)
    return index


_TOOLS_BY_NAME: dict[str, ToolDefinition] = _index_by_name(_CATEGORY_BUNDLES)


# ====================================================
# Доступ к наборам
# ====================================================


def get_toolset(name: Toolset) -> list[ToolDefinition]:
    """
    Возвращает копию набора навыков для указанной сцены.

    Копия, а не сам список из реестра: вызывающий код волен дописать в него
    разовый навык под ситуацию, не задев глобальную конфигурацию.
    """
    return list(_TOOLSETS[name])


def all_tools() -> list[ToolDefinition]:
    """
    Все известные навыки без повторов в стабильном порядке.
    Нужны исполнителю сервисного слоя и тестам полноты реестра.
    """
    return list(_TOOLS_BY_NAME.values())


def find_tool(tool_name: str) -> Optional[ToolDefinition]:
    """
    Ищет определение навыка по имени функции. Возвращает None, если имя реестру
    неизвестно (например, модель придумала несуществующий навык).
    """
    return _TOOLS_BY_NAME.get(tool_name)


__all__ = [
    "Toolset",
    "get_toolset",
    "all_tools",
    "find_tool",
    "GENERAL_TOOLS",
    "STRATEGIC_TOOLS",
    "TACTICAL_TOOLS",
    "DIPLOMACY_TOOLS",
    "GUNSMITH_TOOLS",
    "GAME_MASTER_TOOLS",
    "ADVISOR_TOOLS",
    "CHRONICLER_TOOLS",
]
