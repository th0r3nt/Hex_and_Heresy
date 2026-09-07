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

from backend.l02_services.mechanics.tools.handlers.advisor import AdvisorToolHandlers
from backend.l02_services.mechanics.tools.handlers.chronicler import (
    ChroniclerToolHandlers,
)
from backend.l02_services.mechanics.tools.handlers.diplomacy import (
    DiplomacyToolHandlers,
)
from backend.l02_services.mechanics.tools.handlers.game_master import (
    GameMasterToolHandlers,
)
from backend.l02_services.mechanics.tools.handlers.general import GeneralToolHandlers
from backend.l02_services.mechanics.tools.handlers.gunsmith import GunsmithToolHandlers
from backend.l02_services.mechanics.tools.handlers.strategic import (
    StrategicToolHandlers,
)
from backend.l02_services.mechanics.tools.handlers.tactical import TacticalToolHandlers

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
