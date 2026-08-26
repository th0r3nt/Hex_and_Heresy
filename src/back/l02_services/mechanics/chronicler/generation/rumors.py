"""
Фоновая роль летописца: разносчик слухов.

Когда боев не было несколько тактов, летописец не молчит, а смотрит на
глобальную карту и роняет в окно логов короткую атмосферную фразу
(см. docs/game_mechanics/chronicler.md).
"""

from typing import Optional

from src.back.l01_domain.exceptions.llm import LLMError
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.prompts import (
    PromptCatalog,
    get_chronicler_writing_key,
    get_faction_prompt_key,
)
from src.back.l01_domain.protocols.llm import (
    ContextBuilderProtocol,
    LLMClientProtocol,
    PromptBuilderProtocol,
)
from src.back.l01_domain.world.constants import RUMOR_IDLE_TICKS_THRESHOLD
from src.back.l01_domain.world.models.chronicle import RumorEntry
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.logger import main_logger

RUMOR_TEMPERATURE = 0.95

# Слух - две-три фразы: длинный ответ модели все равно подрежется на входе
# в RumorEntry, но лишние токены тратить незачем
RUMOR_MAX_TOKENS = 200

# TODO: завязать слухи летописца на реальных событиях (напр. если барон отправит караван-экспедицию)


class RumorGenerator:
    """
    Собирает обстановку на глобальной карте и просит модель выдать слух.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        prompt_builder: PromptBuilderProtocol,
        context_builder: ContextBuilderProtocol,
    ) -> None:
        self._llm = llm_client
        self._prompt_builder = prompt_builder
        self._context_builder = context_builder

    def should_speak(
        self,
        world_state: WorldState,
        idle_threshold: int = RUMOR_IDLE_TICKS_THRESHOLD,
    ) -> bool:
        """
        Пора ли разносить слухи. Пока идут бои, летописцу есть чем заняться.
        """
        return world_state.ticks_since_last_battle >= idle_threshold

    async def generate_rumor(
        self, world_state: WorldState, faction: Optional[Faction] = None
    ) -> Optional[RumorEntry]:
        """
        Отдает свежий слух или None, если модель не ответила.

        Слух - украшение интерфейса, а не игровое правило: сбой модели здесь
        логируется и глотается, чтобы не ронять глобальный такт.
        """
        try:
            text = await self._llm.generate_text(
                system_prompt=self._build_prompt(faction),
                user_prompt=f"Сводка мира:\n{self.render_world_context(world_state, faction)}",
                temperature=RUMOR_TEMPERATURE,
                max_tokens=RUMOR_MAX_TOKENS,
            )
        except LLMError as error:
            main_logger.warning(f"[Chronicler] Слух не сгенерирован: {error.message}")
            return None

        if not text.strip():
            return None

        return RumorEntry(
            text=text,
            tick=world_state.time.total_ticks,
            faction_id=faction.id if faction is not None else None,
        )

    # ==================================================================
    # КОНТЕКСТ МИРА
    # ==================================================================

    def render_world_context(
        self, world_state: WorldState, faction: Optional[Faction] = None
    ) -> str:
        """
        Короткая сводка обстановки: время, кризисы, войны и нужда.
        """
        blocks = self._context_builder.build_rumor_context(world_state, faction)
        return self._context_builder.render(blocks)

    def _build_prompt(self, faction: Optional[Faction]) -> str:
        blocks = [
            PromptCatalog.BASE.PERSONA,
            PromptCatalog.ROLES.CHRONICLER.PROMPT,
            get_chronicler_writing_key(faction.race if faction is not None else None),
            PromptCatalog.ROLES.CHRONICLER.RUMORS,
            PromptCatalog.LORE.BASIC.LOW,
        ]
        if faction is not None:
            blocks.append(get_faction_prompt_key(faction.race))

        return self._prompt_builder.build(blocks)
