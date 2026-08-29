"""
Обращение к языковой модели за художественным текстом летописи.

Числа приходят готовыми из BattleLogCollector - здесь решается только то,
чьим голосом и в каком стиле они будут пересказаны. Стиль задает раса
фракции: орки царапают победы на дощечках, баронские писари ведут
бухгалтерию потерь (см. docs/game_mechanics/chronicler.md).
"""

from typing import Optional

from src.back.l01_domain.exceptions.chronicler import ChronicleGenerationFailedError
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
from src.back.l01_domain.world.models.battle_log import BattleDossier
from src.back.l01_domain.world.models.chronicle import (
    FallenKind,
    FallenSubject,
    LLMChronicleResponse,
    LLMEpitaphResponse,
    LLMFinaleResponse,
)

CHRONICLE_TEMPERATURE = 0.85
EPITAPH_TEMPERATURE = 0.75
FINALE_TEMPERATURE = 0.9

# Финал партии пишется один раз за всю игру и боем не датируется: досье
# сражения у него нет, поэтому ошибки модели помечаются этим идентификатором
FINALE_SUBJECT_ID = "finale"


class ChronicleGenerator:
    """
    Просит языковую модель написать страницу летописи или эпитафию.

    Сам ничего не сохраняет и не публикует: это делает фасад.
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

    async def generate_chronicle(
        self,
        dossier: BattleDossier,
        battle_context: str,
        faction: Optional[Faction] = None,
    ) -> LLMChronicleResponse:
        """
        Пишет страницу летописи о сражении по готовой числовой сводке.
        """
        response = await self._ask(
            system_prompt=self._build_chronicle_prompt(dossier, faction),
            user_prompt=f"Сводка сражения:\n{battle_context}",
            response_model=LLMChronicleResponse,
            temperature=CHRONICLE_TEMPERATURE,
            battle_id=dossier.battle_id,
        )

        if not response.body.strip() or not response.title.strip():
            raise ChronicleGenerationFailedError(
                dossier.battle_id, "модель вернула пустую летопись"
            )
        return response

    async def generate_epitaph(
        self,
        subject: FallenSubject,
        dossier: BattleDossier,
        battle_context: str,
        faction: Optional[Faction] = None,
    ) -> LLMEpitaphResponse:
        """
        Пишет некролог для Зала павших: именному отряду или герою.
        """
        response = await self._ask(
            system_prompt=self._build_epitaph_prompt(subject, faction),
            user_prompt=(
                f"Сводка сражения, в котором они полегли:\n{battle_context}\n\n"
                f"{self._describe_subject(subject)}"
            ),
            response_model=LLMEpitaphResponse,
            temperature=EPITAPH_TEMPERATURE,
            battle_id=dossier.battle_id,
        )

        if not response.epitaph.strip():
            raise ChronicleGenerationFailedError(
                dossier.battle_id, f"пустой некролог для '{subject.name}'"
            )
        return response

    async def generate_finale(
        self,
        world_context: str,
        outcome_context: str,
        faction: Optional[Faction] = None,
    ) -> LLMFinaleResponse:
        """
        Пишет последнюю главу хроники: оду триумфатору или реквием павшей
        державе.

        Числа исхода приходят готовыми в outcome_context - генератор только
        решает, чьим голосом их пересказать.
        """
        response = await self._ask(
            system_prompt=self._build_finale_prompt(faction),
            user_prompt=(
                f"Сводка мира:\n{world_context}\n\n"
                f"Чем закончилась партия:\n{outcome_context}"
            ),
            response_model=LLMFinaleResponse,
            temperature=FINALE_TEMPERATURE,
            battle_id=FINALE_SUBJECT_ID,
        )

        if not response.body.strip() or not response.title.strip():
            raise ChronicleGenerationFailedError(
                FINALE_SUBJECT_ID, "модель вернула пустой финал"
            )
        return response

    # ==================================================================
    # СБОРКА ПРОМПТОВ
    # ==================================================================

    def _build_chronicle_prompt(
        self, dossier: BattleDossier, faction: Optional[Faction]
    ) -> str:
        blocks = self._role_blocks(faction)
        blocks.append(PromptCatalog.BASE.MECHANICS.TACTICAL)
        if faction is not None:
            blocks.append(get_faction_prompt_key(faction.race))

        static_context = self._prompt_builder.build(blocks)

        dynamic_context = self._context_builder.render(
            self._context_builder.build_chronicle_context(dossier, faction)
        )
        if not dynamic_context:
            return static_context

        return f"{static_context}\n\n{dynamic_context}"

    def _build_epitaph_prompt(self, subject: FallenSubject, faction: Optional[Faction]) -> str:
        blocks = self._role_blocks(faction)
        if faction is not None:
            blocks.append(get_faction_prompt_key(faction.race))

        static_context = self._prompt_builder.build(blocks)
        who = "герое" if subject.kind == FallenKind.HERO else "именном отряде"

        dynamic_context = (
            f"Сейчас ты пишешь не летопись боя, а надгробную запись о {who} в Зал павших.\n"
            "Напиши некролог в несколько предложений: кем они были и как погибли."
        )

        return f"{static_context}\n\n{dynamic_context}"

    def _build_finale_prompt(self, faction: Optional[Faction]) -> str:
        """
        Промпт финальной главы: к обычному голосу летописца добавляется
        стратегический контекст - итог партии считается по глобальной карте,
        а не по одному сражению.
        """
        blocks = self._role_blocks(faction)
        blocks.append(PromptCatalog.ROLES.CHRONICLER.FINALE)
        blocks.append(PromptCatalog.BASE.MECHANICS.STRATEGIC)
        if faction is not None:
            blocks.append(get_faction_prompt_key(faction.race))

        return self._prompt_builder.build(blocks)

    def _role_blocks(self, faction: Optional[Faction]) -> list[str]:
        """
        Файлы, с которых начинается любой промпт летописца: персона, сама роль
        и стиль записи. Без фракции стиль нейтральный - у боя не было писаря.
        """
        return [
            PromptCatalog.BASE.PERSONA,
            PromptCatalog.ROLES.CHRONICLER.PROMPT,
            get_chronicler_writing_key(faction.race if faction is not None else None),
        ]

    def _describe_subject(self, subject: FallenSubject) -> str:
        """
        Собирает карточку павшего для user_prompt.
        """
        if subject.kind == FallenKind.HERO:
            lines = [f"Погиб герой: {subject.name}."]
        else:
            lines = [
                f"Погиб отряд: {subject.name} ({subject.archetype_name}), "
                f"было {subject.initial_count} бойцов, полегли все."
            ]

        if subject.commander_name:
            lines.append(f"Их вел {subject.commander_name}.")
        if subject.kills:
            lines.append(f"Забрали с собой врагов: {subject.kills}.")
        if subject.killer_name:
            lines.append(f"Их положили: {subject.killer_name}.")

        return "\n".join(lines)

    # ==================================================================
    # СЛУЖЕБНОЕ
    # ==================================================================

    async def _ask(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type,
        temperature: float,
        battle_id: str,
    ):
        """
        Обращается к модели, переводя ее отказы на язык домена: летописец не
        должен ронять такт боя ошибкой сети.
        """
        try:
            return await self._llm.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=response_model,
                temperature=temperature,
            )
        except LLMError as error:
            raise ChronicleGenerationFailedError(battle_id, error.message) from error
