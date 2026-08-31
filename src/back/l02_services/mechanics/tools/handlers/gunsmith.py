"""
Обработчики навыков оружейной мастерской.
"""

from typing import Any

from src.back.l01_domain.llm.tools.definitions.gunsmith import (
    DRAFT_BLUEPRINT,
    REJECT_BLUEPRINT,
)
from src.back.l01_domain.llm.tools.schemas.gunsmith import (
    DraftBlueprintParams,
    RejectBlueprintParams,
)
from src.back.l02_services.mechanics.gunsmith.blueprints import BlueprintRegistry
from src.back.l02_services.mechanics.gunsmith.crafting import (
    LLMGunsmithResponse,
    StatPriorities,
)
from src.back.l02_services.mechanics.gunsmith.facade import GunsmithFacade
from src.back.l02_services.mechanics.gunsmith.validation.balance import EquipmentBalancer
from src.back.l02_services.mechanics.gunsmith.validation.economy import EquipmentEconomist
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor


class GunsmithToolHandlers:
    """
    Вердикт мастера по заказу правителя: чертеж или отказ.
    """

    def __init__(self, gunsmith_facade: GunsmithFacade) -> None:
        self._gunsmith = gunsmith_facade

    def register(self, executor: ToolExecutor) -> None:
        """
        Подключает навыки мастерской к исполнителю.
        """
        executor.register_handler(DRAFT_BLUEPRINT, self.draft_blueprint)
        executor.register_handler(REJECT_BLUEPRINT, self.reject_blueprint)

    # ====================================================
    # Навыки
    # ====================================================

    async def draft_blueprint(
        self, params: DraftBlueprintParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Собирает чертеж по акцентам мастера и заносит его в арсенал фракции.
        """
        faction_id = ctx.require_caller_faction_id("draft_blueprint")

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

        # Автоматическое утверждение чертежа в арсенал фракции
        await self._gunsmith.approve_blueprint(
            world_state=ctx.world_state,
            faction_id=faction_id,
            draft=draft,
        )

        return (
            f"Создан и добавлен в арсенал чертеж «{draft.name}» (тир {draft.tier}). "
            f"Комментарий мастера: {params.master_reply}",
            {"equipment_id": draft.id, "name": draft.name, "tier": draft.tier},
        )

    async def reject_blueprint(
        self, params: RejectBlueprintParams, _ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Закрывает заказ мотивированным отказом мастера.
        """
        return (
            f"Заказ отклонен мастером: {params.master_reply}",
            {"is_approved": False, "reason": params.reason},
        )
