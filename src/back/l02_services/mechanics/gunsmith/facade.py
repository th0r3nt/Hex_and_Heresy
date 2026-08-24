"""
Главный фасад механики Оружейника.
Оркестрирует LLM, балансировщик, экономику и реестр чертежей.
"""

from typing import Optional

from src.back.l01_domain.army.models.card.equipment import Equipment
from src.back.l01_domain.factions.constants import ResourceType
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.gunsmith.crafting import LLMGunsmithResponse
from src.back.l02_services.mechanics.gunsmith.blueprints import BlueprintRegistry
from src.back.l02_services.mechanics.gunsmith.validation.balance import EquipmentBalancer
from src.back.l02_services.mechanics.gunsmith.validation.economy import EquipmentEconomist
from src.back.utils.event.registry import GameEvents


class GunsmithFacade:
    def __init__(
        self,
        llm_client: LLMClientProtocol,
        event_bus: Optional[EventBusProtocol] = None,
    ) -> None:
        self._llm = llm_client
        self._event_bus = event_bus

    async def draft_blueprint(
        self, faction_id: str, user_request: str
    ) -> tuple[Optional[Equipment], str]:
        """
        Запрашивает у Мастера создание нового чертежа по текстовому описанию игрока.
        Возвращает кортеж: (чертеж_если_одобрен, текстовый_ответ_мастера).
        """
        system_prompt = self._build_gunsmith_system_prompt(faction_id)

        # Вызываем LLM со строгой Pydantic-схемой
        response = await self._llm.generate_structured(
            system_prompt=system_prompt,
            user_prompt=f"Заказ от правителя:\n{user_request}",
            response_model=LLMGunsmithResponse,
            temperature=0.7,
        )

        # Мастер отказался делать этот бред
        if not response.is_approved or response.priorities is None or response.tier is None:
            if self._event_bus:
                await self._event_bus.publish(
                    GameEvents.Gunsmith.BLUEPRINT_REJECTED,
                    faction_id=faction_id,
                    reason=response.master_reply,
                )
            return None, response.master_reply

        # 1. Считаем баланс статов
        stats = EquipmentBalancer.normalize_stats(response.tier, response.priorities)

        # 2. Считаем цену
        gold, material = EquipmentEconomist.calculate_cost(response.tier, response.tags)

        # 3. Собираем чертеж
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

        # Плата за исследования и внедрение (Research & Development)
        # Списываем разово стоимость крафта 1 предмета
        faction.spend(ResourceType.GOLD, draft.cost_gold)
        faction.spend(ResourceType.MATERIAL, draft.cost_material)

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

    def _build_gunsmith_system_prompt(self, faction_id: str) -> str:
        """
        Собирает промпт для LLM. На бою он будет брать markdown файлы из
        инфраструктуры, но логика выглядит так:
        """
        # TODO: Интегрировать с llm.prompt_builder для склейки реальных файлов.
        # Пока используем жесткий каркас для наглядности:
        return (
            "Ты — Оружейный мастер темного фэнтези мира Hex & Heresy.\n"
            f"Твоя фракция: {faction_id}.\n"
            "Твоя задача — оценивать заказы своего лорда на новое оружие, броню или аксессуары.\n\n"
            "Правила:\n"
            "1. Не нарушай лор. Отказывай в стиле своей расы.\n"
            "2. Одобряй логичные заказы и распределяй приоритеты характеристик от 0 до 10.\n"
            "3. Например, если оружие должно быть огромным и мощным, ставь высокий приоритет урону, но обязательно выкручивай штраф к весу.\n"
            "4. Отвечай лорным комментарием в поле master_reply - ты общаешься с лордом лично."
        )
