"""
Обработчики навыков по категориям.

Каждый модуль держит свой класс `*ToolHandlers`: зависимости (фасады) он
получает в конструкторе, а методом `register(executor)` подключает свою пачку
навыков к `ToolExecutor`. Имя метода-обработчика совпадает с именем навыка,
поэтому по `ToolCall.name` всегда видно, куда смотреть.

Обработчик - тонкая прослойка: разобрать схему параметров, позвать метод
фасада и пересказать результат словами для модели. Логика и проверки правил
живут в домене и сервисах.
"""

from src.back.l02_services.mechanics.tools.handlers.advisor import AdvisorToolHandlers
from src.back.l02_services.mechanics.tools.handlers.chronicler import (
    ChroniclerToolHandlers,
)
from src.back.l02_services.mechanics.tools.handlers.diplomacy import (
    DiplomacyToolHandlers,
)
from src.back.l02_services.mechanics.tools.handlers.game_master import (
    GameMasterToolHandlers,
)
from src.back.l02_services.mechanics.tools.handlers.general import GeneralToolHandlers
from src.back.l02_services.mechanics.tools.handlers.gunsmith import GunsmithToolHandlers
from src.back.l02_services.mechanics.tools.handlers.strategic import (
    StrategicToolHandlers,
)
from src.back.l02_services.mechanics.tools.handlers.tactical import TacticalToolHandlers

__all__ = [
    "AdvisorToolHandlers",
    "ChroniclerToolHandlers",
    "DiplomacyToolHandlers",
    "GameMasterToolHandlers",
    "GeneralToolHandlers",
    "GunsmithToolHandlers",
    "StrategicToolHandlers",
    "TacticalToolHandlers",
]
