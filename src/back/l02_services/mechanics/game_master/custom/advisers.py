"""
Фабрика генерации кастомных советников фракции.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from src.back.l01_domain.army.models.characters.traits import (
    TRAITS_CATALOG,
    Trait,
    format_traits_prompt,
    get_trait,
)
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions.llm import LLMError
from src.back.l01_domain.llm.prompts import PromptCatalog, get_faction_prompt_key
from src.back.l01_domain.protocols.llm import LLMClientProtocol, PromptBuilderProtocol
from src.back.utils.logger import main_logger


@dataclass(frozen=True)
class CustomAdvisor:
    """Профиль советника для UI и генерации рекомендаций."""

    id: str
    faction_id: str
    race: FactionRace
    name: str
    title: str
    personality_prompt: str
    biography: str
    traits: list[Trait]

    def get_traits_prompt(self) -> str:
        """Возвращает форматированный блок черт советника."""
        return format_traits_prompt(self.traits)


class CustomAdvisorDraftResponse(BaseModel):
    """Схема ответа мастера игры при создании советника."""

    is_lore_friendly: bool = Field(..., description="Соответствует ли советник лору")
    rejection_reason: Optional[str] = Field(default=None, description="Причина отказа")
    name: str = Field(default="Советник", description="Имя советника")
    title: str = Field(default="Первый советник", description="Должность или звание")
    distilled_personality: str = Field(
        default="", description="Тон общения, манера давать советы и приоритеты"
    )
    selected_trait_ids: list[str] = Field(
        default_factory=list, description="Идентификаторы черт из каталога"
    )


class CustomAdvisorFactory:
    """Генерирует профили советников на основе текста игрока."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        prompt_builder: PromptBuilderProtocol,
    ) -> None:
        self._llm = llm_client
        self._prompt_builder = prompt_builder

    async def create_advisor(
        self,
        faction_id: str,
        race: FactionRace,
        biography_text: str,
    ) -> tuple[Optional[CustomAdvisor], str]:
        """Парсит биографию и возвращает профиль советника."""
        system_prompt = self._build_system_prompt(race)
        user_prompt = f"Описание советника от игрока:\n{biography_text}"

        try:
            draft = await self._llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=CustomAdvisorDraftResponse,
                temperature=0.6,
            )
        except LLMError as e:
            main_logger.error(f"[GameMaster] Ошибка генерации советника: {e.message}")
            return None, f"Мастер игры временно недоступен: {e.message}"

        if not draft.is_lore_friendly or draft.rejection_reason:
            reason = draft.rejection_reason or "Концепт советника отклонен мастером игры."
            return None, reason

        attached_traits = []
        for tid in draft.selected_trait_ids:
            trait = get_trait(tid)
            if trait is not None and trait not in attached_traits:
                attached_traits.append(trait)

        advisor = CustomAdvisor(
            id=f"adv_custom_{uuid4().hex[:8]}",
            faction_id=faction_id,
            race=race,
            name=draft.name,
            title=draft.title,
            personality_prompt=draft.distilled_personality,
            biography=biography_text,
            traits=attached_traits,
        )

        return advisor, f"Советник {advisor.title} {advisor.name} готов к службе."

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
            "Создай советника для правителя фракции.\n"
            "1. Выбери от 1 до 3 подходящих ключей черт в selected_trait_ids:\n"
            f"{traits_summary}\n"
            "2. Сформулируй стиль речи и характер советника (например, суровый бюрократ, язвительный циник, фанатичный инквизитор)."
        )
        return f"{base_prompt}\n\n{instructions}"
