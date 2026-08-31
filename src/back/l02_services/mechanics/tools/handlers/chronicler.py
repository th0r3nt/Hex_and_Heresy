"""
Обработчики навыков внутриигрового летописца.
"""

from typing import Any

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.llm.tools.definitions.chronicler import (
    RECORD_CHRONICLE,
    RECORD_EPITAPH,
    RECORD_FINALE,
    SPEAK_RUMOR,
)
from src.back.l01_domain.llm.tools.schemas.chronicler import (
    RecordChronicleParams,
    RecordEpitaphParams,
    RecordFinaleParams,
    SpeakRumorParams,
)
from src.back.l01_domain.world.models.chronicle import (
    ChronicleEntry,
    FallenRecord,
    FinaleChronicle,
    RumorEntry,
)
from src.back.l02_services.mechanics.chronicler.facade import ChroniclerFacade
from src.back.l02_services.mechanics.tools.context import ToolExecutionContext
from src.back.l02_services.mechanics.tools.executor import ToolExecutor


class ChroniclerToolHandlers:
    """
    Летопись партии: страницы хроник, эпитафии павшим, финал и слухи.

    Актором в контексте приезжает то, о чем пишут: бой для хроники и отряд
    для надгробия.
    """

    def __init__(self, chronicler_facade: ChroniclerFacade) -> None:
        self._chronicler = chronicler_facade

    def register(self, executor: ToolExecutor) -> None:
        """
        Подключает навыки летописца к исполнителю.
        """
        executor.register_handler(RECORD_CHRONICLE, self.record_chronicle)
        executor.register_handler(RECORD_EPITAPH, self.record_epitaph)
        executor.register_handler(RECORD_FINALE, self.record_finale)
        executor.register_handler(SPEAK_RUMOR, self.speak_rumor)

    # ====================================================
    # Навыки
    # ====================================================

    async def record_chronicle(
        self, params: RecordChronicleParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Вносит в архив страницу хроники о прошедшем бое.
        """
        battle_id = ctx.actor_id or "battle_latest"
        entry = ChronicleEntry(
            battle_id=battle_id,
            title=params.title,
            quote=params.quote,
            body=params.body,
            tick=ctx.world_state.time.total_ticks,
            faction_id=ctx.caller_faction_id,
        )
        await self._chronicler._archive.record_battle(ctx.world_state, entry)
        return (
            f"Записана страница летописи: «{entry.title}».",
            {"chronicle_id": entry.id, "battle_id": battle_id},
        )

    async def record_epitaph(
        self, params: RecordEpitaphParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Хоронит павший отряд в Зале павших с надгробной надписью.
        """
        squad_id = ctx.actor_id or "squad_unknown"
        record = FallenRecord(
            squad_id=squad_id,
            squad_name=params.title,
            race=FactionRace.HUMANS,
            faction_id=ctx.caller_faction_id,
            title=params.title,
            epitaph=params.epitaph,
            death_tick=ctx.world_state.time.total_ticks,
        )
        await self._chronicler._hall.bury(ctx.world_state, record)
        return (
            f"В Зал павших внесено надгробие: «{record.squad_name}».",
            {"record_id": record.id, "squad_name": record.squad_name},
        )

    async def record_finale(
        self, params: RecordFinaleParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Записывает финальную главу хроники завершившейся партии.
        """
        finale = FinaleChronicle(
            is_player_victorious=True,
            reason=params.title,
            title=params.title,
            body=params.body,
            tick=ctx.world_state.time.total_ticks,
            faction_id=ctx.caller_faction_id,
        )
        ctx.world_state.set_finale(finale)
        return (
            f"Записана финальная глава хроники: «{finale.title}».",
            {"finale_id": finale.id, "title": finale.title},
        )

    async def speak_rumor(
        self, params: SpeakRumorParams, ctx: ToolExecutionContext
    ) -> tuple[str, dict[str, Any]]:
        """
        Пускает по державам слух о делах минувшего такта.
        """
        rumor = RumorEntry(
            text=params.text,
            tick=ctx.world_state.time.total_ticks,
            faction_id=ctx.caller_faction_id,
        )
        await self._chronicler._archive.record_rumor(ctx.world_state, rumor)
        return (
            f"Опубликован слух: «{rumor.text}».",
            {"rumor_id": rumor.id, "text": rumor.text},
        )
