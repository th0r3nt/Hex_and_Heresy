"""
Определения инструментов дипломатических переговоров и соглашений.
"""

from src.back.l01_domain.llm.models.tools import ToolDefinition
from src.back.l01_domain.llm.tools.schemas.diplomacy import (
    DeclareWarParams,
    DemandTributeParams,
    EstablishBordersParams,
    EstablishRightOfPassageParams,
    ExecuteAmbassadorParams,
    MakePeaceParams,
    PayTributeParams,
    ProposeTradeParams,
    RecallAmbassadorParams,
    SendAmbassadorParams,
    SendDispatchParams,
)

DECLARE_WAR = ToolDefinition(
    name="declare_war",
    description="Объявить войну другой державе, аннулируя все активные мирные пакты.",
    parameters_model=DeclareWarParams,
)

MAKE_PEACE = ToolDefinition(
    name="make_peace",
    description="Заключить мирный договор и прекратить состояние войны.",
    parameters_model=MakePeaceParams,
)

PROPOSE_TRADE = ToolDefinition(
    name="propose_trade",
    description="Предложить регулярный пассивный обмен ресурсами между державами.",
    parameters_model=ProposeTradeParams,
)

ESTABLISH_BORDERS = ToolDefinition(
    name="establish_borders",
    description="Заключить пакт о ненападении и зафиксировать границы территорий.",
    parameters_model=EstablishBordersParams,
)

ESTABLISH_RIGHT_OF_PASSAGE = ToolDefinition(
    name="establish_right_of_passage",
    description="Предоставить право прохода армий через свои земли за плату или бесплатно.",
    parameters_model=EstablishRightOfPassageParams,
)

DEMAND_TRIBUTE = ToolDefinition(
    name="demand_tribute",
    description="Выставить другой державе требование о выплате дани золотом.",
    parameters_model=DemandTributeParams,
)

EXECUTE_AMBASSADOR = ToolDefinition(
    name="execute_ambassador",
    description="Казнить чужого посла в тронном зале, немедленно начав войну.",
    parameters_model=ExecuteAmbassadorParams,
)

SEND_DISPATCH = ToolDefinition(
    name="send_dispatch",
    description="Нанять конного гонца и отправить письменную депешу правителю другой державы.",
    parameters_model=SendDispatchParams,
)

SEND_AMBASSADOR = ToolDefinition(
    name="send_ambassador",
    description="Снарядить и отправить посла для личных переговоров в цитадели другой державы.",
    parameters_model=SendAmbassadorParams,
)

RECALL_AMBASSADOR = ToolDefinition(
    name="recall_ambassador",
    description="Отозвать посла с аудиенции обратно домой.",
    parameters_model=RecallAmbassadorParams,
)

PAY_TRIBUTE = ToolDefinition(
    name="pay_tribute",
    description="Выплатить затребованную другой державой дань золотом из казны.",
    parameters_model=PayTributeParams,
)
