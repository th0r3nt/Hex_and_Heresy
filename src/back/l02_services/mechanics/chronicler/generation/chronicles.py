"""
Обращение к языковой модели за художественным текстом летописи.

Числа приходят готовыми из BattleLogCollector - здесь решается только то,
чьим голосом и в каком стиле они будут пересказаны. Стиль задает раса
фракции: орки царапают победы на дощечках, баронские писари ведут
бухгалтерию потерь (см. docs/game_mechanics/chronicler.md).
"""

from typing import Optional

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.exceptions import ChronicleGenerationFailedError, LLMError
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l01_domain.world.models.battle_log import BattleDossier
from src.back.l01_domain.world.models.chronicle import (
    FallenKind,
    FallenSubject,
    LLMChronicleResponse,
    LLMEpitaphResponse,
)
from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder
from src.back.l03_infrastructure.llm.prompt.catalog import (
    PromptCatalog,
    get_faction_prompt_path,
)

CHRONICLE_TEMPERATURE = 0.85
EPITAPH_TEMPERATURE = 0.75

# Перенести в llm/prompts/
RACE_STYLE_FRAGMENTS: dict[FactionRace, str] = {
    FactionRace.HUMANS: (
        "Ты пишешь в дорогой книге ровным фэнтезийным слогом. В тексте уместны "
        "упоминания инквизиции, костров и веры в то, что павшие исполнили долг."
    ),
    FactionRace.GREENSKINS: (
        "Ты царапаешь запись на деревянной табличке кровью. Пиши коротко, грубо и "
        "радостно: хорошая драка важнее потерь, а слабых не жалеют."
    ),
    FactionRace.ELFS: (
        "Ты выводишь тонкие светящиеся строки в изящной книге. Пиши отстраненно и "
        "печально, как существо, пережившее сотни таких битв."
    ),
    FactionRace.BARONIAL_TROOPS: (
        "Ты ведешь бухгалтерский учет войны. Пиши сухо и предельно ровно, считай "
        "убытки и амортизацию снаряжения, эмоции держи при себе."
    ),
    FactionRace.CONGREGATION_OF_THE_METEORITE: (
        "Ты высекаешь текст на табличке из магического обсидиана. Пиши как "
        "проповедь: смерть - это подношение, а метеорит все видит."
    ),
    FactionRace.MERCENARIES: (
        "Ты заполняешь отчет для нанимателя. Пиши деловито: кто заплатил, что "
        "стоило крови и во сколько обошелся контракт."
    ),
}

BASE_CHRONICLER_PROMPT = (
    "Ты - летописец темного постапокалиптического фэнтези мира Hex & Heresy. "
    "Тебе приносят сухую сводку сражения: числа потерь, имена отрядов и "
    "переломные моменты.\n"
    "Твоя работа - превратить эту математику в живой текст.\n\n"
    "Правила:\n"
    "1. Не ломай четвертую стену: ты житель этого мира, а не рассказчик игры.\n"
    "2. Не выдумывай события, которых нет в сводке. Имена, числа и исход - "
    "только оттуда.\n"
    "3. Опирайся на переломные моменты: паника, удар во фланг, осечка, гора трупов.\n"
    "4. Безымянное ополчение хорони общими словами, именные отряды называй поименно."
)


def race_style_fragment(faction: Optional[Faction]) -> str:
    """
    Стилистический фрагмент промпта для расы фракции.
    Без фракции летописец пишет нейтрально: так бывает для боев наемников
    и стычек на ничьей земле, где нет своего писаря.
    """
    if faction is None:
        return "Ты пишешь нейтральной хроникой стороннего наблюдателя."
    return RACE_STYLE_FRAGMENTS.get(
        faction.race, "Ты пишешь нейтральной хроникой стороннего наблюдателя."
    )


class ChronicleGenerator:
    """
    Просит языковую модель написать страницу летописи или эпитафию.

    Сам ничего не сохраняет и не публикует: это делает фасад.
    """

    def __init__(
        self, llm_client: LLMClientProtocol, prompt_builder: Optional[PromptBuilder] = None
    ) -> None:
        self._llm = llm_client
        self._prompt_builder = prompt_builder or PromptBuilder()

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

    # ==================================================================
    # СБОРКА ПРОМПТОВ
    # ==================================================================

    def _build_chronicle_prompt(
        self, dossier: BattleDossier, faction: Optional[Faction]
    ) -> str:
        blocks = [
            PromptCatalog.BASE.PERSONA,
            PromptCatalog.ROLES.CHRONICLER,
            PromptCatalog.BASE.MECHANICS.TACTICAL,
        ]
        if faction is not None:
            blocks.append(get_faction_prompt_path(faction.race))

        static_context = self._prompt_builder.build(blocks)

        dynamic_lines = [
            "Тебе приносят сухую сводку сражения: числа потерь, имена отрядов и переломные моменты.",
            "Преврати эту математику в живой текст.",
            "Не выдумывай события, которых нет в сводке.",
        ]

        if faction is not None:
            dynamic_lines.append(
                f"Ты служишь фракции '{faction.name}': чужие потери считай заслуженными."
            )
        if dossier.is_siege:
            dynamic_lines.append("Это был штурм цитадели - событие, которое запомнят надолго.")
        if dossier.is_massacre:
            dynamic_lines.append("Одну из сторон вырезали почти полностью: это была резня.")

        dynamic_context = "\n".join(dynamic_lines)
        return f"{static_context}\n\n{dynamic_context}"

    def _build_epitaph_prompt(self, subject: FallenSubject, faction: Optional[Faction]) -> str:
        blocks = [PromptCatalog.BASE.PERSONA, PromptCatalog.ROLES.CHRONICLER]
        if faction is not None:
            blocks.append(get_faction_prompt_path(faction.race))

        static_context = self._prompt_builder.build(blocks)
        who = "герое" if subject.kind == FallenKind.HERO else "именном отряде"

        dynamic_context = (
            f"Сейчас ты пишешь не летопись боя, а надгробную запись о {who} в Зал павших.\n"
            "Напиши некролог в несколько предложений: кем они были и как погибли."
        )

        return f"{static_context}\n\n{dynamic_context}"

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
