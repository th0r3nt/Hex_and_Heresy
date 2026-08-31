"""
Разговор с советником: плановое предложение, ответ на вопрос игрока и
запрос действий после сделанного выбора через Function Calling.
"""

from typing import Optional

from src.back.l01_domain.exceptions.advisor import AdvisorGenerationFailedError
from src.back.l01_domain.exceptions.llm import LLMError
from src.back.l01_domain.factions.models.advisor import (
    ADVISOR_MAX_OPTIONS,
    AdvisorAnswer,
    AdvisorOption,
    AdvisorOptionKind,
    AdvisorProposal,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.models.tools import ToolCall
from src.back.l01_domain.llm.prompts import PromptCatalog, get_faction_prompt_key
from src.back.l01_domain.llm.tools.definitions.advisor import PROPOSE_ADVISOR_ACTION
from src.back.l01_domain.llm.tools.schemas.advisor import ProposeAdvisorActionParams
from src.back.l01_domain.protocols.llm import (
    ContextBuilderProtocol,
    LLMClientProtocol,
    PromptBuilderProtocol,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l01_domain.llm.tools.catalog import Toolset, get_toolset
from src.back.utils.logger import main_logger

FREEFORM_OPTION_LABEL = "Дать свой ответ"


class AdvisorGenerator:
    """
    Собирает промпты советника и управляет вызовами инструментов советника.
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

    # ==================================================================
    # Пассивная инициатива
    # ==================================================================

    async def generate_proposal(
        self,
        world_state: WorldState,
        faction: Faction,
        personality_prompt: str = "",
    ) -> Optional[AdvisorProposal]:
        """
        Советник осматривает державу и при наличии повода вызывает инструмент
        propose_advisor_action.
        """
        system_prompt = self._build_system_prompt(
            world_state, faction, personality_prompt, self._PROPOSAL_INSTRUCTIONS
        )
        tools = get_toolset(Toolset.ADVISOR_COUNCIL)

        try:
            _content, tool_calls = await self._llm.generate_with_tools(
                system_prompt=system_prompt,
                user_prompt=(
                    "Наступил новый глобальный такт. Осмотри державу и, если есть повод, "
                    "вызови инструмент."
                ),
                tools=tools,
                temperature=0.7,
            )
        except LLMError as error:
            main_logger.warning(f"[Advisor] Ошибка генерации предложения: {error.message}")
            return None

        # Ищем вызов инструмента предложения
        proposal_call = next(
            (call for call in tool_calls if call.name == PROPOSE_ADVISOR_ACTION.name),
            None,
        )
        if proposal_call is None:
            return None

        try:
            params = proposal_call.parse_arguments(ProposeAdvisorActionParams)
        except Exception as error:
            main_logger.warning(f"[Advisor] Невалидные параметры предложения: {error}")
            return None

        if not params.message.strip():
            return None

        return AdvisorProposal(
            faction_id=faction.id,
            tick=world_state.time.total_ticks,
            title=params.title.strip() or "Доклад советника",
            message=params.message,
            options=self._build_options(params.options),
        )

    # ==================================================================
    # Диалоговый режим
    # ==================================================================

    async def answer_question(
        self,
        world_state: WorldState,
        faction: Faction,
        question: str,
        personality_prompt: str = "",
    ) -> AdvisorAnswer:
        """
        Советник отвечает на вопрос игрока в свободной форме.
        """
        system_prompt = self._build_system_prompt(
            world_state, faction, personality_prompt, self._DIALOGUE_INSTRUCTIONS
        )

        try:
            text = await self._llm.generate_text(
                system_prompt=system_prompt,
                user_prompt=f"Правитель спрашивает:\n{question}",
                temperature=0.8,
            )
        except LLMError as error:
            raise AdvisorGenerationFailedError(faction.id, error.message) from error

        if not text.strip():
            raise AdvisorGenerationFailedError(faction.id, "модель вернула пустой ответ")

        return AdvisorAnswer(faction_id=faction.id, question=question, text=text.strip())

    # ==================================================================
    # Действия после выбора игрока
    # ==================================================================

    async def request_actions(
        self,
        world_state: WorldState,
        faction: Faction,
        proposal: AdvisorProposal,
        option: AdvisorOption,
        player_reply: str = "",
        personality_prompt: str = "",
    ) -> tuple[str, list[ToolCall]]:
        """
        Игрок сделал выбор: советник отвечает репликой и вызывает соответствующие
        инструменты управления (set_tax_rate, assign_worker и т.д.).
        """
        choice_text = f"Правитель выбрал вариант «{option.label}»."
        if player_reply.strip():
            choice_text = f"{choice_text}\nСлова правителя:\n{player_reply.strip()}"

        system_prompt = self._build_system_prompt(
            world_state, faction, personality_prompt, self._EXECUTION_INSTRUCTIONS
        )
        user_prompt = (
            f"Твое предложение:\n{proposal.message}\n\n"
            f"{choice_text}\n\n"
            "Примени необходимые инструменты для выполнения решения правителя и подтверди его словами."
        )
        tools = get_toolset(Toolset.STRATEGIC_TURN)

        try:
            content, tool_calls = await self._llm.generate_with_tools(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=tools,
                temperature=0.7,
            )
        except LLMError as error:
            main_logger.warning(f"[Advisor] Ошибка ответа на выбор: {error.message}")
            content, tool_calls = "", []

        reply = content.strip() or "Советник молча склоняет голову и приступает к исполнению."
        return reply, tool_calls

    # ==================================================================
    # Сборка промптов
    # ==================================================================

    def _build_system_prompt(
        self,
        world_state: WorldState,
        faction: Faction,
        personality_prompt: str,
        instructions: str,
    ) -> str:
        static_context = self._prompt_builder.build(
            [
                PromptCatalog.BASE.PERSONA,
                PromptCatalog.BASE.MECHANICS.ECONOMY,
                PromptCatalog.BASE.MECHANICS.STRATEGIC,
                PromptCatalog.ROLES.ADVISOR,
                get_faction_prompt_key(faction.race),
                PromptCatalog.LORE.BASIC.MEDIUM,
            ]
        )

        dynamic_context = self._context_builder.render(
            self._context_builder.build_advisor_context(world_state, faction)
        )

        parts = [static_context, dynamic_context]
        if personality_prompt.strip():
            parts.append(f"## Твоя личность\n{personality_prompt.strip()}")
        parts.append(instructions)

        return "\n\n".join(part for part in parts if part.strip())

    def _build_options(self, option_labels: list[str]) -> list[AdvisorOption]:
        """
        Приводит подписи кнопок от модели к контракту интерфейса.

        Свободный ответ добавляется последним и всегда: возразить советнику
        своими словами игрок вправе, даже если тот такой кнопки не предложил.
        Свою кнопку с той же подписью модель рисовать не должна - иначе в окне
        окажутся две одинаковые, и лишь одна откроет поле ввода.
        """
        options = [
            AdvisorOption(label=label, kind=AdvisorOptionKind.ACCEPT)
            for label in option_labels
            if label.strip() and label.strip().casefold() != FREEFORM_OPTION_LABEL.casefold()
        ]

        if not options:
            options = [
                AdvisorOption(label="Принять", kind=AdvisorOptionKind.ACCEPT),
                AdvisorOption(label="Отклонить", kind=AdvisorOptionKind.DECLINE),
            ]

        options = options[: ADVISOR_MAX_OPTIONS - 1]
        options.append(
            AdvisorOption(label=FREEFORM_OPTION_LABEL, kind=AdvisorOptionKind.FREEFORM)
        )
        return options

    # TODO: засунуть в промпты
    _PROPOSAL_INSTRUCTIONS = (
        "## Задача советника\n"
        "Осмотри срез державы и реши, есть ли повод для доклада правителю.\n"
        "1. Если обстановка стабильна, не вызывай никаких инструментов.\n"
        "2. Если требуется решение правителя, вызови инструмент propose_advisor_action, "
        "передав заголовок, краткий совет и 2-3 варианта выбора (например, «Поднять на 10%», «Поднять на 5%»)."
    )

    # TODO: засунуть в промпты
    _DIALOGUE_INSTRUCTIONS = (
        "## Задача советника\n"
        "Правитель обратился к тебе лично. Ответь коротко и по существу, "
        "опираясь только на факты из среза мира выше."
    )

    # TODO: засунуть в промпты
    _EXECUTION_INSTRUCTIONS = (
        "## Задача советника\n"
        "Правитель утвердил решение. Вызови необходимые прикладные инструменты "
        "(например, set_tax_rate, assign_worker и др.) и кратко подтверди выполнение."
    )
