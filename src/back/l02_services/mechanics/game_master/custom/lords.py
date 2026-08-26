"""
Фабрика генерации кастомных лордов (правителей фракций) на основе модульных черт.
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.army.models.characters.traits import (
    TRAITS_CATALOG,
    get_trait,
)
from src.back.l01_domain.common import CharacterGenerationType, FactionRace
from src.back.l01_domain.exceptions.llm import LLMError
from src.back.l01_domain.factions.models.lord import (
    Lord,
)
from src.back.l01_domain.llm.prompts import PromptCatalog, get_faction_prompt_key
from src.back.l01_domain.protocols.llm import LLMClientProtocol, PromptBuilderProtocol
from src.back.utils.logger import main_logger


class CustomLordDraftResponse(BaseModel):
    """Схема ответа мастера игры при создании лорда."""

    is_lore_friendly: bool = Field(..., description="Соответствует ли лорд сеттингу")
    rejection_reason: Optional[str] = Field(default=None, description="Причина отказа")
    name: str = Field(default="Правитель", description="Имя правителя")
    title: str = Field(default="Лорд", description="Титул (Барон, Канцлер, Вождь и т.д.)")
    archetype_name: str = Field(default="Правитель", description="Стиль руководства")
    archetype_description: str = Field(default="", description="Описание внутренней политики")
    distilled_personality: str = Field(
        default="", description="Манера общения на дипломатических аудиенциях"
    )
    selected_trait_ids: list[str] = Field(
        default_factory=list, description="Идентификаторы черт из каталога"
    )

    # Стратегические уклоны лорда (-1.0 .. 1.0)
    tax_rate_bias: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Склонность к повышению налогов"
    )
    military_building_priority: float = Field(
        default=0.0, ge=-1.0, le=1.0, description="Приоритет военной застройки"
    )
    diplomatic_aggression: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Агрессивность во внешней политике"
    )
    bribery_susceptibility: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Сговорчивость при подкупе золотом"
    )


class CustomLordFactory:
    """Генерирует правителей фракций на основе биографии игрока."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        prompt_builder: PromptBuilderProtocol,
    ) -> None:
        self._llm = llm_client
        self._prompt_builder = prompt_builder

    async def create_lord(
        self,
        faction_id: str,
        race: FactionRace,
        biography_text: str,
    ) -> tuple[Optional[Lord], str]:
        """Парсит биографию и возвращает агрегат Lord."""
        system_prompt = self._build_system_prompt(race)
        user_prompt = f"Описание правителя от игрока:\n{biography_text}"

        try:
            draft = await self._llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=CustomLordDraftResponse,
                temperature=0.6,
            )
        except LLMError as e:
            main_logger.error(f"[GameMaster] Ошибка генерации лорда: {e.message}")
            return None, f"Мастер игры временно недоступен: {e.message}"

        if not draft.is_lore_friendly or draft.rejection_reason:
            reason = draft.rejection_reason or "Концепт правителя отклонен мастером игры."
            return None, reason

        attached_traits = []
        for tid in draft.selected_trait_ids:
            trait = get_trait(tid)
            if trait is not None and trait not in attached_traits:
                attached_traits.append(trait)

        lord = Lord(
            faction_id=faction_id,
            name=draft.name,
            title=draft.title,
            generation_type=CharacterGenerationType.CUSTOM,
            traits=attached_traits,
            custom_biography=biography_text,
            personality_prompt_override=draft.distilled_personality,
        )

        return lord, f"{lord.display_name} принимает правление фракцией."

    def _build_system_prompt(self, race: FactionRace) -> str:
        blocks = [
            PromptCatalog.BASE.PERSONA,
            PromptCatalog.ROLES.GAME_MASTER,
            get_faction_prompt_key(race),
            PromptCatalog.LORE.BASIC.MEDIUM,
        ]
        base_prompt = self._prompt_builder.build(blocks)

        traits_summary = "\n".join(
            f"- {tid}: {t.name} ({t.category.value})" for tid, t in TRAITS_CATALOG.items()
        )

        # TODO: засунуть в промпты
        instructions = (
            "## Задача мастера игры\n"
            "Создай правителя (лорда) фракции на основе запроса игрока.\n"
            "1. Подбери титул и имя, аутентичные культуре расы.\n"
            "2. Выбери от 1 до 3 подходящих ключей черт в selected_trait_ids:\n"
            f"{traits_summary}\n"
            "3. Настрой уклоны ИИ (налоги, военная застройка, агрессия, подкуп от -1.0 до 1.0).\n"
            "4. Сформулируй distilled_personality для ведения переговоров с другими лордами."
        )
        return f"{base_prompt}\n\n{instructions}"
