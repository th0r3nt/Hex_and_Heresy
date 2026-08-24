"""
Фоновая роль летописца: разносчик слухов.

Когда боев не было несколько тактов, летописец не молчит, а смотрит на
глобальную карту и роняет в окно логов короткую атмосферную фразу
(см. docs/game_mechanics/chronicler.md).
"""

from typing import Optional

from src.back.l01_domain.exceptions import LLMError
from src.back.l01_domain.factions.constants import DiplomaticStance, ResourceType
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l01_domain.world.constants import RUMOR_IDLE_TICKS_THRESHOLD
from src.back.l01_domain.world.models.chronicle import RumorEntry
from src.back.l01_domain.world.models.state import WorldState
from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder
from src.back.l03_infrastructure.llm.prompt.catalog import (
    PromptCatalog,
    get_faction_prompt_path,
)
from src.back.utils.logger import main_logger

RUMOR_TEMPERATURE = 0.95

# Слух - две-три фразы: длинный ответ модели все равно подрежется на входе
# в RumorEntry, но лишние токены тратить незачем
RUMOR_MAX_TOKENS = 200

# Ниже этого запаса еды фракция считается голодающей: слухи о пустых амбарах
RUMOR_HUNGER_THRESHOLD = 50.0

BASE_RUMOR_PROMPT = (
    "Ты - летописец темного постапокалиптического фэнтези мира Hex & Heresy. "
    "Боев нет, и ты собираешь то, о чем шепчутся на дорогах и в тавернах.\n\n"
    "Правила:\n"
    "1. Одна-две фразы, не больше. Это строка в окне слухов, а не рассказ.\n"
    "2. Опирайся только на то, что сказано в сводке мира.\n"
    "3. Никаких обращений к игроку и никаких пояснений - только сам слух.\n"
    "Пример тона: «Торговцы говорят, что барон опять поднял налоги. "
    "В Черных топях неспокойно»."
)
# TODO: завязать слухи летописца на реальных событиях (напр. если барон отправит караван-экспедицию)


class RumorGenerator:
    """
    Собирает обстановку на глобальной карте и просит модель выдать слух.
    """

    def __init__(
        self, llm_client: LLMClientProtocol, prompt_builder: Optional[PromptBuilder] = None
    ) -> None:
        self._llm = llm_client
        self._prompt_builder = prompt_builder or PromptBuilder()

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
        lines = [
            f"- Время: {world_state.time.format_timestamp()}.",
            f"- Боев не было тактов: {world_state.ticks_since_last_battle}.",
        ]

        events = [event for event in world_state.active_events if event.is_active]
        if events:
            names = ", ".join(f"«{event.name}»" for event in events[:5])
            lines.append(f"- Идут события: {names}.")

        wars = self._render_wars(world_state)
        if wars:
            lines.append(f"- Войны: {wars}.")

        if faction is not None:
            lines.append(
                f"- Ты пишешь для фракции '{faction.name}' (раса: {faction.race.value})."
            )
            food = faction.resources.get(ResourceType.FOOD, 0.0)
            if food < RUMOR_HUNGER_THRESHOLD:
                lines.append(f"- В закромах фракции осталось еды: {food:.0f}. Люди голодают.")

        battlefields = [
            site for site in world_state.battlefield_sites.values() if not site.is_depleted
        ]
        if battlefields:
            lines.append(f"- На карте гниют поля брани: {len(battlefields)}.")

        return "\n".join(lines)

    def _render_wars(self, world_state: WorldState) -> str:
        """
        Перечисляет воюющие пары фракций человеческими именами.
        """
        wars = []
        for relation in world_state.diplomatic_relations:
            if relation.stance != DiplomaticStance.WAR:
                continue
            first = world_state.get_faction(relation.faction_a_id)
            second = world_state.get_faction(relation.faction_b_id)
            wars.append(
                f"{first.name if first else relation.faction_a_id} против "
                f"{second.name if second else relation.faction_b_id}"
            )
        return "; ".join(wars)

    def _build_prompt(self, faction: Optional[Faction]) -> str:
        blocks = [
            PromptCatalog.BASE.PERSONA,
            PromptCatalog.ROLES.CHRONICLER,
            PromptCatalog.LORE.BASIC.LOW,
        ]
        if faction is not None:
            blocks.append(get_faction_prompt_path(faction.race))

        static_context = self._prompt_builder.build(blocks)

        dynamic_context = (
            "Боев нет, и ты собираешь то, о чем шепчутся на дорогах и в тавернах.\n"
            "Напиши одну-две фразы. Никаких обращений к игроку — только сам слух."
        )

        return f"{static_context}\n\n{dynamic_context}"
