"""
Фабрика сборщика диспетчера инструментов ToolExecutor.
"""

from typing import Optional

from src.back.l02_services.mechanics.advisor.facade import AdvisorFacade
from src.back.l02_services.mechanics.chronicler.facade import ChroniclerFacade
from src.back.l02_services.mechanics.diplomacy.facade import DiplomacyFacade
from src.back.l02_services.mechanics.game_master.facade import GameMasterFacade
from src.back.l02_services.mechanics.gunsmith.facade import GunsmithFacade
from src.back.l02_services.mechanics.tools.executor import ToolExecutor
from src.back.l02_services.mechanics.tools.handlers import (
    AdvisorToolHandlers,
    ChroniclerToolHandlers,
    DiplomacyToolHandlers,
    GameMasterToolHandlers,
    GeneralToolHandlers,
    GunsmithToolHandlers,
    StrategicToolHandlers,
    TacticalToolHandlers,
)
from src.back.l02_services.turns.facade import TurnsFacade


def build_tool_executor(
    turns_facade: Optional[TurnsFacade] = None,
    diplomacy_facade: Optional[DiplomacyFacade] = None,
    gunsmith_facade: Optional[GunsmithFacade] = None,
    game_master_facade: Optional[GameMasterFacade] = None,
    chronicler_facade: Optional[ChroniclerFacade] = None,
    advisor_facade: Optional[AdvisorFacade] = None,
) -> ToolExecutor:
    """
    Создает экземпляр ToolExecutor и регистрирует в нем все доступные наборы
    обработчиков.

    Набор без своего фасада просто не подключается: без него модель все равно
    не сможет ничего сделать, а исполнитель вернет честный отказ «навык не
    поддерживается».
    """
    executor = ToolExecutor()

    # 1. Общие и тактические навыки (фасадов не требуют)
    GeneralToolHandlers().register(executor)
    TacticalToolHandlers().register(executor)

    # 2. Фасадные навыки при наличии соответствующих зависимостей
    if turns_facade is not None:
        StrategicToolHandlers(turns_facade).register(executor)
    if diplomacy_facade is not None:
        DiplomacyToolHandlers(diplomacy_facade).register(executor)
    if gunsmith_facade is not None:
        GunsmithToolHandlers(gunsmith_facade).register(executor)
    if game_master_facade is not None:
        GameMasterToolHandlers(game_master_facade).register(executor)
    if chronicler_facade is not None:
        ChroniclerToolHandlers(chronicler_facade).register(executor)
    if advisor_facade is not None:
        AdvisorToolHandlers(advisor_facade).register(executor)

    return executor
