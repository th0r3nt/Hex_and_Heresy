"""
Определения инструментов глобальной стратегической карты.
"""

from src.back.l01_domain.llm.models.tools import ToolDefinition
from src.back.l01_domain.llm.tools.schemas.strategic import (
    AssignWorkerParams,
    ClaimBorderLandParams,
    DispatchExpeditionParams,
    FoundBorderTownParams,
    OrderArmyMarchParams,
    ResolveBorderTownParams,
    SetTaxRateParams,
    StationSquadParams,
    UnassignWorkerParams,
    UnstationSquadParams,
    UpgradeBorderTownParams,
)

ORDER_ARMY_MARCH = ToolDefinition(
    name="order_army_march",
    description="Приказать армии начать марш к указанному гексу на глобальной карте.",
    parameters_model=OrderArmyMarchParams,
)

SET_TAX_RATE = ToolDefinition(
    name="set_tax_rate",
    description="Установить новую налоговую ставку для фракции.",
    parameters_model=SetTaxRateParams,
)

ASSIGN_WORKER = ToolDefinition(
    name="assign_worker",
    description="Назначить отряд рабочих на экономическое здание для стационарной добычи.",
    parameters_model=AssignWorkerParams,
)

UNASSIGN_WORKER = ToolDefinition(
    name="unassign_worker",
    description="Снять отряд рабочих с экономического здания.",
    parameters_model=UnassignWorkerParams,
)

DISPATCH_EXPEDITION = ToolDefinition(
    name="dispatch_expedition",
    description="Отправить караван рабочих в экспедицию на нейтральный гекс за ресурсами.",
    parameters_model=DispatchExpeditionParams,
)

FOUND_BORDER_TOWN = ToolDefinition(
    name="found_border_town",
    description="Основать новый пограничный город на свободном нейтральном гексе.",
    parameters_model=FoundBorderTownParams,
)

UPGRADE_BORDER_TOWN = ToolDefinition(
    name="upgrade_border_town",
    description="Улучшить пограничный город на следующий уровень развития.",
    parameters_model=UpgradeBorderTownParams,
)

CLAIM_BORDER_LAND = ToolDefinition(
    name="claim_border_land",
    description="Выкупить смежный нейтральный гекс в качестве союзной земли пограничного города.",
    parameters_model=ClaimBorderLandParams,
)

RESOLVE_BORDER_TOWN = ToolDefinition(
    name="resolve_border_town",
    description="Решить судьбу побежденного пограничного города (сжечь, разграбить, занять или пропустить).",
    parameters_model=ResolveBorderTownParams,
)

STATION_SQUAD = ToolDefinition(
    name="station_squad",
    description="Расквартировать отряд регулярной армии в гарнизон земли за крепостные стены.",
    parameters_model=StationSquadParams,
)

UNSTATION_SQUAD = ToolDefinition(
    name="unstation_squad",
    description="Вывести отряд из гарнизона крепостных стен обратно в полевую армию.",
    parameters_model=UnstationSquadParams,
)
