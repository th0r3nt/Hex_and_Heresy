"""
Главный фасад механики Оружейника.
Оркестрирует LLM, балансировщик, экономику и реестр чертежей.
"""

from typing import Optional

from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.llm.prompts import PromptCatalog, get_faction_prompt_key
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.llm import (
    ContextBuilderProtocol,
    LLMClientProtocol,
    PromptBuilderProtocol,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l02_services.mechanics.gunsmith.crafting import LLMGunsmithResponse
from src.back.l02_services.mechanics.gunsmith.blueprints import BlueprintRegistry
from src.back.l02_services.mechanics.gunsmith.validation.balance import EquipmentBalancer
from src.back.l02_services.mechanics.gunsmith.validation.economy import EquipmentEconomist
from src.back.utils.event.registry import GameEvents


class GunsmithFacade:
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

        # Вызываем LLM
        response = await self._llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=f"Заказ от правителя:\n{user_request}",
            response_model=LLMGunsmithResponse,
            temperature=0.7,
        )

        # Мастер отказался делать этот бред - либо ответил так, что считать нечего:
        # без приоритетов не собрать статы, без тира - бюджет и цену,
        # без слота домен не примет карточку
        if (
            not response.is_approved
            or response.priorities is None
            or response.tier is None
            or response.slot is None
        ):
            if self._event_bus:
                await self._event_bus.publish(
                    GameEvents.Gunsmith.BLUEPRINT_REJECTED,
                    faction_id=faction_id,
                    reason=response.master_reply,
                )
            return None, response.master_reply

        stats = EquipmentBalancer.normalize_stats(response.tier, response.priorities)
        gold, material = EquipmentEconomist.calculate_cost(response.tier, response.tags)
        draft = BlueprintRegistry.construct_draft(response, stats, gold, material)

        if self._event_bus:
            await self._event_bus.publish(
                GameEvents.Gunsmith.BLUEPRINT_DRAFTED,
                faction_id=faction_id,
                equipment_id=draft.id,
                equipment_name=draft.name,
            )

        return draft, response.master_reply

    async def approve_blueprint(
        self, world_state: WorldState, faction_id: str, draft: Equipment
    ) -> None:
        """
        Игрок соглашается с чертежом.
        Оплачивается R&D (стоимость производства 1 штуки как плата за разработку),
        и чертеж добавляется в арсенал партии.
        """
        faction = world_state.get_faction(faction_id)
        if not faction:
            raise ValueError(f"Фракция {faction_id} не найдена")

        # Плата за исследования и внедрение (Research & Development).
        # Списываем разово стоимость крафта 1 предмета - и сразу оба ресурса:
        # заплатить золотом и остаться без чертежа из-за нехватки материалов нельзя.
        faction.spend_all(
            {
                ResourceType.GOLD: draft.cost_gold,
                ResourceType.MATERIAL: draft.cost_material,
            }
        )

        # Добавляем в реестр кастомных предметов текущей партии
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
        # Статика
        static_context = self._prompt_builder.build([
            PromptCatalog.BASE.PERSONA,
            PromptCatalog.BASE.MECHANICS.ECONOMY,
            PromptCatalog.ROLES.GUNSMITH,
            get_faction_prompt_key(faction.race),
            PromptCatalog.LORE.BASIC.MEDIUM
        ])

        # Динамика через билдер
        blocks = self._context_builder.build_gunsmith_context(world_state, faction)
        dynamic_context = self._context_builder.render(blocks)

        return f"{static_context}\n\n{dynamic_context}"
