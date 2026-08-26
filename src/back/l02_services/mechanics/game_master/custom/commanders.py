"""
Фабрика генерации кастомных полководцев на основе модульных черт.
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.army.models.characters.commanders import (
    Commander,
    CommanderCharacteristics,
)
from src.back.l01_domain.army.models.characters.traits import (
    TRAITS_CATALOG,
    get_trait,
)
from src.back.l01_domain.common import CharacterGenerationType, FactionRace
from src.back.l01_domain.exceptions.llm import LLMError
from src.back.l01_domain.llm.prompts import PromptCatalog, get_faction_prompt_key
from src.back.l01_domain.protocols.llm import LLMClientProtocol, PromptBuilderProtocol
from src.back.utils.logger import main_logger


class CustomCommanderDraftResponse(BaseModel):
    """Схема ответа мастера игры при создании полководца."""

    is_lore_friendly: bool = Field(
        ..., description="Соответствует ли персонаж и его способности мрачному лору вселенной"
    )
    rejection_reason: Optional[str] = Field(
        default=None,
        description="Стилизованный отказ (например, от Зала инквизиции), если концепт нарушает мир",
    )
    name: str = Field(default="Безымянный командир", description="Имя персонажа")
    archetype_name: str = Field(default="Полководец", description="Воинское звание или роль")
    archetype_description: str = Field(default="", description="Описание воинской доктрины")
    distilled_personality: str = Field(
        default="", description="Сжатое описание характера и манеры речи для промпта"
    )

    # Список выбранных черт из доступного каталога (1-3 ключа)
    selected_trait_ids: list[str] = Field(
        default_factory=list,
        description="Идентификаторы черт из каталога (напр. ['craven', 'deserter'])",
    )

    # Базовые числовые характеристики командира (0..100)
    authority: int = Field(default=10, ge=0, le=100)
    tactical_acumen: int = Field(default=10, ge=0, le=100)
    resilience: int = Field(default=10, ge=0, le=100)
    cunning: int = Field(default=10, ge=0, le=100)


class CustomCommanderFactory:
    """Генерирует полководцев на основе текста игрока и каталога черт."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        prompt_builder: PromptBuilderProtocol,
    ) -> None:
        self._llm = llm_client
        self._prompt_builder = prompt_builder

    async def create_commander(
        self,
        faction_id: str,
        race: FactionRace,
        biography_text: str,
    ) -> tuple[Optional[Commander], str]:
        """
        Парсит биографию и возвращает агрегат Commander с прикрепленными чертами.
        """

        system_prompt = self._build_system_prompt(race)
        user_prompt = f"Описание полководца от игрока:\n{biography_text}"

        try:
            draft = await self._llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=CustomCommanderDraftResponse,
                temperature=0.6,
            )
        except LLMError as e:
            main_logger.error(f"[GameMaster] Ошибка генерации полководца: {e.message}")
            return None, f"Мастер игры временно недоступен: {e.message}"

        if not draft.is_lore_friendly or draft.rejection_reason:
            reason = draft.rejection_reason or "Концепт персонажа отклонен мастером игры."
            return None, reason

        # Подтягиваем объекты Trait из единого каталога
        attached_traits = []
        for tid in draft.selected_trait_ids:
            trait = get_trait(tid)
            if trait is not None and trait not in attached_traits:
                attached_traits.append(trait)

        characteristics = CommanderCharacteristics(
            authority=draft.authority,
            tactical_acumen=draft.tactical_acumen,
            resilience=draft.resilience,
            cunning=draft.cunning,
        )

        commander = Commander(
            name=draft.name,
            role_title=draft.archetype_name,
            faction_id=faction_id,
            generation_type=CharacterGenerationType.CUSTOM,
            traits=attached_traits,
            characteristics=characteristics,
            custom_biography=biography_text,
            personality_prompt_override=draft.distilled_personality,
        )

        return commander, f"Полководец {commander.name} готов занять место в ставке."

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
            "Проанализируй текст игрока и создай кастомного полководца.\n"
            "1. Проверь концепт на лор: анахронизмы (кибернетика, светлая магия маны, лазеры) — отклоняй "
            "через is_lore_friendly: false и стилизованный rejection_reason.\n"
            "2. Выбери от 1 до 3 подходящих ключей черт в selected_trait_ids из списка доступных:\n"
            f"{traits_summary}\n"
            "3. Оцени базовые характеристики полководца (authority, tactical_acumen, resilience, cunning) в диапазоне 0..100.\n"
            "4. Сформулируй distilled_personality для манеры речи модели в диалогах."
        )
        return f"{base_prompt}\n\n{instructions}"
