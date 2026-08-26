"""
Фабрика генерации кастомных героев на основе модульных черт.
"""

from typing import Optional
from pydantic import BaseModel, Field

from src.back.l01_domain.army.models.characters.heroes import (
    Hero
)
from src.back.l01_domain.army.models.characters.traits import (
    TRAITS_CATALOG,
    get_trait,
)
from src.back.l01_domain.common import CharacterGenerationType, FactionRace
from src.back.l01_domain.exceptions.llm import LLMError
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder
from src.back.l03_infrastructure.llm.prompt.catalog import (
    PromptCatalog,
    get_faction_prompt_path,
)
from src.back.utils.logger import main_logger


class CustomHeroDraftResponse(BaseModel):
    """Схема ответа мастера игры при создании героя."""

    is_lore_friendly: bool = Field(..., description="Соответствует ли герой сеттингу")
    rejection_reason: Optional[str] = Field(default=None, description="Причина отказа")
    name: str = Field(default="Безымянный герой", description="Имя героя")
    archetype_name: str = Field(default="Поединщик", description="Название героической роли")
    archetype_description: str = Field(default="", description="Описание боевых навыков")
    special_rule: str = Field(
        default="Неукротимый боец",
        description="Текстовое описание уникальной способности на поле боя",
    )
    max_hp: float = Field(
        default=120.0, ge=50.0, le=400.0, description="Базовый запас здоровья героя"
    )
    distilled_personality: str = Field(
        default="", description="Черты характера и манера поведения героя"
    )
    selected_trait_ids: list[str] = Field(
        default_factory=list, description="Идентификаторы черт из каталога"
    )


class CustomHeroFactory:
    """Генерирует доменных героев на основе биографии игрока."""

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        prompt_builder: Optional[PromptBuilder] = None,
    ) -> None:
        self._llm = llm_client
        self._prompt_builder = prompt_builder or PromptBuilder()

    async def create_hero(
        self,
        faction_id: str,
        race: FactionRace,
        biography_text: str,
    ) -> tuple[Optional[Hero], str]:
        """Парсит биографию и возвращает агрегат Hero."""
        system_prompt = self._build_system_prompt(race)
        user_prompt = f"Описание героя от игрока:\n{biography_text}"

        try:
            draft = await self._llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=CustomHeroDraftResponse,
                temperature=0.6,
            )
        except LLMError as e:
            main_logger.error(f"[GameMaster] Ошибка генерации героя: {e.message}")
            return None, f"Мастер игры временно недоступен: {e.message}"

        if not draft.is_lore_friendly or draft.rejection_reason:
            reason = draft.rejection_reason or "Концепт героя отклонен мастером игры."
            return None, reason

        attached_traits = []
        for tid in draft.selected_trait_ids:
            trait = get_trait(tid)
            if trait is not None and trait not in attached_traits:
                attached_traits.append(trait)


        hero = Hero.create_new(
            name=draft.name,
            faction_id=faction_id,
            special_rule=draft.special_rule,
            max_hp=draft.max_hp,
            traits=attached_traits,
            generation_type=CharacterGenerationType.CUSTOM,
            custom_biography=biography_text,
            personality_prompt_override=draft.distilled_personality,
        )

        return hero, f"Герой {hero.name} готов примкнуть к вашей армии."

    def _build_system_prompt(self, race: FactionRace) -> str:
        blocks = [
            PromptCatalog.BASE.PERSONA,
            PromptCatalog.ROLES.GAME_MASTER,
            get_faction_prompt_path(race),
            PromptCatalog.LORE.BASIC.MEDIUM,
        ]
        base_prompt = self._prompt_builder.build(blocks)

        traits_summary = "\n".join(
            f"- {tid}: {t.name} ({t.category.value})" for tid, t in TRAITS_CATALOG.items()
        )
        # TODO: засунуть в промпты
        instructions = (
            "## Задача мастера игры\n"
            "Создай героическую карточку на основе запроса игрока.\n"
            "1. Герой занимает 1 клетку, но сопоставим по силе с отрядом солдат.\n"
            "2. Сформулируй special_rule (уникальную способность или тактическое правило).\n"
            "3. Выбери от 1 до 3 подходящих ключей черт в selected_trait_ids:\n"
            f"{traits_summary}\n"
            "4. Отрегулируй max_hp (обычно 80..200, у чудовищ до 350)."
        )
        return f"{base_prompt}\n\n{instructions}"
