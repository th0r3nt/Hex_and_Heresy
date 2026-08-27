"""
Разговор с советником: плановое предложение, ответ на вопрос игрока и
запрос действий после сделанного выбора.

Модуль знает только протоколы языковой модели и сборщиков промптов - откуда
берутся тексты ролей и как устроен клиент, ему неизвестно.
"""

from typing import Optional

from src.back.l01_domain.exceptions.advisor import AdvisorGenerationFailedError
from src.back.l01_domain.exceptions.llm import LLMError
from src.back.l01_domain.factions.models.advisor import (
    ADVISOR_MAX_OPTIONS,
    AdvisorAction,
    AdvisorAnswer,
    AdvisorOption,
    AdvisorOptionKind,
    AdvisorProposal,
    LLMAdvisorOption,
    LLMAdvisorProposalResponse,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.llm.prompts import PromptCatalog, get_faction_prompt_key
from src.back.l01_domain.protocols.llm import (
    ContextBuilderProtocol,
    LLMClientProtocol,
    PromptBuilderProtocol,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.utils.logger import main_logger

# Кнопка свободного ответа есть в окне всегда: игрок вправе возразить словами
FREEFORM_OPTION_LABEL = "Дать свой ответ"


class AdvisorGenerator:
    """
    Собирает промпты советника и превращает ответы модели в доменные модели.
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
    # ПАССИВНАЯ ИНИЦИАТИВА
    # ==================================================================

    async def generate_proposal(
        self,
        world_state: WorldState,
        faction: Faction,
        personality_prompt: str = "",
    ) -> Optional[AdvisorProposal]:
        """
        Советник осматривает державу и решает, есть ли повод для окна.

        Возвращает None, если повода нет или модель не ответила: непрошеный
        совет - украшение хода, а не игровое правило, и ронять из-за него
        глобальный такт незачем.
        """
        system_prompt = self._build_system_prompt(
            world_state, faction, personality_prompt, self._PROPOSAL_INSTRUCTIONS
        )

        try:
            draft = await self._llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=(
                    "Наступил новый глобальный такт. Осмотри державу и реши, "
                    "стоит ли беспокоить правителя."
                ),
                response_model=LLMAdvisorProposalResponse,
                temperature=0.7,
            )
        except LLMError as error:
            main_logger.warning(f"[Advisor] Ошибка генерации предложения: {error.message}")
            return None

        if not draft.should_speak or not draft.message.strip():
            return None

        return AdvisorProposal(
            faction_id=faction.id,
            tick=world_state.time.total_ticks,
            title=draft.title.strip() or "Доклад советника",
            message=draft.message,
            options=self._build_options(draft.options),
        )

    # ==================================================================
    # ДИАЛОГОВЫЙ РЕЖИМ
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

        Здесь молчание - это уже отказ в обслуживании: игрок открыл окно и
        ждет ответа, поэтому ошибка модели летит наружу.
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

        return AdvisorAnswer(
            faction_id=faction.id, question=question, text=text.strip()
        )

    # ==================================================================
    # ДЕЙСТВИЯ ПОСЛЕ ВЫБОРА ИГРОКА
    # ==================================================================

    async def request_actions(
        self,
        world_state: WorldState,
        faction: Faction,
        proposal: AdvisorProposal,
        option: AdvisorOption,
        player_reply: str = "",
        personality_prompt: str = "",
    ) -> tuple[str, list[AdvisorAction]]:
        """
        Игрок сделал выбор - советник подтверждает его словами и берется за дело.

        Возвращает реплику советника и список намерений для исполнителя.

        ЗАГЛУШКА в части намерений: выбирать действия советник обязан только
        через навыки Function Calling, а их схемы еще не описаны. 
        Пока список всегда пуст, и до мира решение игрока не доходит - 
        интерфейс узнает об этом из статуса NOT_SUPPORTED у исполнителя.
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
            "Ответь правителю одной-двумя фразами."
        )

        try:
            reply = await self._llm.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
            )
        except LLMError as error:
            main_logger.warning(f"[Advisor] Ошибка ответа на выбор: {error.message}")
            reply = ""

        # TODO: заменить на вызов навыков, когда появятся схемы Function Calling
        actions: list[AdvisorAction] = []

        return reply.strip() or "Советник молча склоняет голову.", actions

    # ==================================================================
    # СБОРКА ПРОМПТОВ
    # ==================================================================

    def _build_system_prompt(
        self,
        world_state: WorldState,
        faction: Faction,
        personality_prompt: str,
        instructions: str,
    ) -> str:
        """
        Склеивает статику роли, срез мира, личность советника и задачу такта.
        """
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

    def _build_options(
        self, drafted: list[LLMAdvisorOption]
    ) -> list[AdvisorOption]:
        """
        Приводит кнопки модели к контракту интерфейса.

        Свободный ответ добавляется последним и всегда: возразить советнику
        своими словами игрок вправе, даже если тот такой кнопки не предложил.
        """
        options = [
            AdvisorOption(label=item.label, kind=item.kind)
            for item in drafted
            if item.label.strip() and item.kind != AdvisorOptionKind.FREEFORM
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

    # ==================================================================
    # ЗАДАЧИ СОВЕТНИКА
    # ==================================================================

    # TODO: засунуть в промпты
    _PROPOSAL_INSTRUCTIONS = (
        "## Задача советника\n"
        "Осмотри срез державы и реши, есть ли повод для доклада правителю.\n"
        "1. Не спамь: если казна полна, границы спокойны, а стройки идут, "
        "выстави should_speak: false.\n"
        "2. Говори об одном конкретном деле, а не обо всем сразу: пустая казна "
        "при заниженном налоге, голод, брошенная стройка, чужая армия у столицы.\n"
        "3. Предложи 2-3 варианта ответа: согласие (kind: accept), смягченный "
        "или усиленный вариант (kind: adjust) и отказ (kind: decline). "
        "Подписи кнопок короткие и конкретные: «Поднять на 10%», «Поднять на 5%»."
    )

    # TODO: засунуть в промпты
    _DIALOGUE_INSTRUCTIONS = (
        "## Задача советника\n"
        "Правитель обратился к тебе лично. Ответь коротко и по существу, "
        "опираясь только на факты из среза мира выше. Не выдумывай того, чего "
        "в отчетах нет: чего не знаешь - о том так и скажи."
    )

    # TODO: засунуть в промпты
    _EXECUTION_INSTRUCTIONS = (
        "## Задача советника\n"
        "Правитель ответил на твое предложение. Подтверди его решение "
        "одной-двумя фразами в своей манере: без списков и без пересказа "
        "самого предложения."
    )
