"""
Главный фасад механики оружейника.
Оркестрирует LLM через инструменты, балансировщик, экономику и реестр чертежей.
"""

from typing import Optional

from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.exceptions.llm import InvalidToolCallError
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.prompts import PromptCatalog, get_faction_prompt_key
from src.back.l01_domain.llm.tools.definitions.gunsmith import (
    DRAFT_BLUEPRINT,
    REJECT_BLUEPRINT,
)
from src.back.l01_domain.llm.tools.schemas.gunsmith import (
    DraftBlueprintParams,
    RejectBlueprintParams,
)
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.llm import (
    ContextBuilderProtocol,
    LLMClientProtocol,
    PromptBuilderProtocol,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.gunsmith.blueprints import BlueprintRegistry
from src.back.l02_services.mechanics.gunsmith.crafting import (
    LLMGunsmithResponse,
    StatPriorities,
)
from src.back.l02_services.mechanics.gunsmith.validation.balance import EquipmentBalancer
from src.back.l02_services.mechanics.gunsmith.validation.economy import EquipmentEconomist
from src.back.l01_domain.llm.tools.catalog import Toolset, get_toolset
from src.back.utils.event.registry import GameEvents

# Реплика мастера на вызов навыка с недозаполненными параметрами
INCOMPLETE_ANSWER_REPLY = "Мастер повертел заказ в руках и вернул его: чертеж так не собрать."


class GunsmithFacade:
    """
    Фасад взаимодействия с мастером-оружейником.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        prompt_builder: PromptBuilderProtocol,
        context_builder: ContextBuilderProtocol,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._llm = llm_client
        self._prompt_builder = prompt_builder
        self._context_builder = context_builder
        self._event_bus = event_bus

    async def draft_blueprint(
        self, world_state: WorldState, faction_id: str, user_request: str
    ) -> tuple[Optional[Equipment], str]:
        faction = world_state.get_faction(faction_id)
        if not faction:
            raise ValueError(f"Фракция {faction_id} не найдена")

        system_prompt = self._build_gunsmith_system_prompt(world_state, faction)
        tools = get_toolset(Toolset.GUNSMITH_WORKSHOP)

        content, tool_calls = await self._llm.generate_with_tools(
            system_prompt=system_prompt,
            user_prompt=f"Заказ от правителя:\n{user_request}",
            tools=tools,
            temperature=0.7,
        )

        # 1. Проверяем отказ мастера
        reject_call = next(
            (call for call in tool_calls if call.name == REJECT_BLUEPRINT.name), None
        )
        if reject_call is not None:
            try:
                reject_params = reject_call.parse_arguments(RejectBlueprintParams)
            except InvalidToolCallError:
                return await self._refuse(faction_id, INCOMPLETE_ANSWER_REPLY)
            return await self._refuse(faction_id, reject_params.master_reply)

        # 2. Проверяем создание чертежа
        draft_call = next(
            (call for call in tool_calls if call.name == DRAFT_BLUEPRINT.name), None
        )
        if draft_call is None:
            reply = content.strip() or "Мастер не смог спроектировать такой чертеж."
            return None, reply

        # Недозаполненный вызов - это тот же отказ мастера, а не ошибка сервера:
        # без слота, имени или внятного тира домен карточку все равно не примет,
        # и игроку полезнее реплика мастерской, чем красный экран валидации.
        try:
            params = draft_call.parse_arguments(DraftBlueprintParams)
        except InvalidToolCallError:
            return await self._refuse(faction_id, INCOMPLETE_ANSWER_REPLY)

        priorities = StatPriorities(
            damage=params.damage_priority,
            armor_piercing=params.armor_piercing_priority,
            armor_bonus=params.armor_bonus_priority,
            range_hexes=params.range_priority,
            heavy_weight_tradeoff=params.heavy_weight_tradeoff,
            clunkiness_tradeoff=params.clunkiness_tradeoff,
        )

        response_draft = LLMGunsmithResponse(
            is_approved=True,
            master_reply=params.master_reply,
            name=params.name,
            lore=params.lore,
            tier=params.tier,
            slot=params.slot,
            category_name=params.category_name,
            tags=params.tags,
            priorities=priorities,
            special_rules=params.special_rules,
        )

        stats = EquipmentBalancer.normalize_stats(params.tier, priorities)
        gold, material = EquipmentEconomist.calculate_cost(params.tier, params.tags)
        draft = BlueprintRegistry.construct_draft(response_draft, stats, gold, material)

        if self._event_bus:
            await self._event_bus.publish(
                GameEvents.Gunsmith.BLUEPRINT_DRAFTED,
                faction_id=faction_id,
                equipment_id=draft.id,
                equipment_name=draft.name,
            )

        return draft, params.master_reply

    async def _refuse(
        self, faction_id: str, master_reply: str
    ) -> tuple[None, str]:
        """
        Закрывает заказ отказом мастера: чертежа нет, игрок получает реплику.
        """
        if self._event_bus:
            await self._event_bus.publish(
                GameEvents.Gunsmith.BLUEPRINT_REJECTED,
                faction_id=faction_id,
                reason=master_reply,
            )
        return None, master_reply

    async def approve_blueprint(
        self, world_state: WorldState, faction_id: str, draft: Equipment
    ) -> None:
        faction = world_state.get_faction(faction_id)
        if not faction:
            raise ValueError(f"Фракция {faction_id} не найдена")

        faction.spend_all(
            {
                ResourceType.GOLD: draft.cost_gold,
                ResourceType.MATERIAL: draft.cost_material,
            }
        )

        world_state.add_custom_equipment(draft)

        if self._event_bus:
            await self._event_bus.publish(
                GameEvents.Gunsmith.BLUEPRINT_APPROVED,
                faction_id=faction_id,
                equipment_id=draft.id,
                equipment_name=draft.name,
                cost_gold=draft.cost_gold,
                cost_material=draft.cost_material,
            )

    def _build_gunsmith_system_prompt(self, world_state: WorldState, faction: Faction) -> str:
        static_context = self._prompt_builder.build(
            [
                PromptCatalog.BASE.PERSONA,
                PromptCatalog.BASE.MECHANICS.ECONOMY,
                PromptCatalog.ROLES.GUNSMITH,
                get_faction_prompt_key(faction.race),
                PromptCatalog.LORE.BASIC.MEDIUM,
            ]
        )

        blocks = self._context_builder.build_gunsmith_context(world_state, faction)
        dynamic_context = self._context_builder.render(blocks)

        return f"{static_context}\n\n{dynamic_context}"
