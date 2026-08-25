"""
Фасад.
Точка входа для остальных модулей.

Летописец собирает числовой лог боя (BattleLogCollector), решает, достойно ли
сражение пера, просит языковую модель пересказать его словами и складывает
результат в летопись и Зал павших.

Языковая модель необязательна: без нее летописец продолжает вести досье боев
и молча копит числа - партия от этого не ломается, просто свитков не будет.
"""

from typing import Any, Optional

from src.back.utils.logger import main_logger

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.models.reports import TacticalTurnReport
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.exceptions.chronicler import (
    BattleDossierNotFoundError,
    ChronicleGenerationFailedError,
)
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.protocols.chronicler import ChroniclerRepositoryProtocol
from src.back.l01_domain.protocols.events import EventBusProtocol
from src.back.l01_domain.protocols.llm import LLMClientProtocol
from src.back.l01_domain.world.constants import (
    CHRONICLE_HISTORY_PAGE_SIZE,
    CHRONICLE_MIN_SQUADS_PER_SIDE,
)
from src.back.l01_domain.world.models.battle_log import BattleDossier, BattleSide
from src.back.l01_domain.world.models.chronicle import (
    ChronicleEntry,
    FallenRecord,
    FallenSubject,
    RumorEntry,
)
from src.back.l01_domain.world.models.state import WorldState
from src.back.l02_services.mechanics.chronicler.archives.fallens import HallOfFallen
from src.back.l02_services.mechanics.chronicler.archives.history import ChronicleArchive
from src.back.l02_services.mechanics.chronicler.generation.battles import BattleLogCollector
from src.back.l02_services.mechanics.chronicler.generation.chronicles import ChronicleGenerator
from src.back.l02_services.mechanics.chronicler.generation.rumors import RumorGenerator

from src.back.l03_infrastructure.llm.context.builder import ContextBuilder
from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder


class ChroniclerFacade:
    """
    Оркестрирует сбор боевого лога, генерацию текстов и архивы летописи.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClientProtocol] = None,
        repository: Optional[ChroniclerRepositoryProtocol] = None,
        event_bus: Optional[EventBusProtocol] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        context_builder: Optional[ContextBuilder] = None,
    ) -> None:
        self._event_bus = event_bus
        self._collector = BattleLogCollector()
        self._archive = ChronicleArchive(repository=repository, event_bus=event_bus)
        self._hall = HallOfFallen(repository=repository, event_bus=event_bus)

        pb = prompt_builder or PromptBuilder()
        cb = context_builder or ContextBuilder()
        self._chronicles = (
            ChronicleGenerator(llm_client, pb, cb) if llm_client is not None else None
        )
        self._rumors = (
            RumorGenerator(llm_client, pb, cb) if llm_client is not None else None
        )

    # ==================================================================
    # ХОД БОЯ
    # ==================================================================

    def on_battle_started(
        self,
        world_state: WorldState,
        battle_state: TacticalBattleState,
        squads: dict[str, Squad],
        strategic_hex: Optional[HexCoordinates] = None,
    ) -> BattleDossier:
        """
        Заводит досье боя. Вызывается до первого раунда: позже исходную
        численность сторон уже не восстановить.
        """
        return self._collector.start_battle(
            world_state=world_state,
            battle_state=battle_state,
            squads=squads,
            strategic_hex=strategic_hex,
        )

    def on_battle_turn(self, report: TacticalTurnReport) -> Optional[BattleDossier]:
        """
        Разносит числа очередного раунда по досье.

        Бой, начало которого летописец пропустил, пересказать нельзя, но и
        ронять из-за этого тактический такт незачем: пропуск логируется.
        """
        try:
            return self._collector.absorb_turn(report)
        except BattleDossierNotFoundError as error:
            main_logger.warning(f"[Chronicler] {error.message}")
            return None

    async def chronicle_battle(
        self, world_state: WorldState, report: TacticalTurnReport
    ) -> Optional[ChronicleEntry]:
        """
        Закрывает бой: считает итоги, при необходимости пишет летопись и
        хоронит именные отряды.

        Возвращает страницу летописи или None, если бой оказался проходной
        стычкой либо модель не ответила.
        """
        try:
            dossier = self._collector.finalize(report)
        except BattleDossierNotFoundError as error:
            main_logger.warning(f"[Chronicler] {error.message}")
            return None

        world_state.register_battle_happened()

        try:
            if not self.is_chronicle_worthy(dossier):
                main_logger.debug(
                    f"[Chronicler] Бой '{dossier.battle_id}' не дотянул до летописи."
                )
                return None

            entry = await self._write_chronicle(world_state, dossier)
            await self._bury_named_squads(world_state, dossier)
            return entry
        finally:
            self._collector.discard(dossier.battle_id)

    def note_hero_slain(self, battle_id: str, hero_name: str) -> None:
        """
        Отмечает павшего героя в досье боя, чтобы летопись его не забыла.

        TODO: полноценное надгробие герою в Зале павших появится вместе с
        механикой гибели героев в тактическом бою - сейчас урон по героям
        нигде не наносится, и событие HERO_SLAIN никто не публикует.
        """
        dossier = self._collector.get_dossier(battle_id)
        if dossier is None:
            main_logger.warning(
                f"[Chronicler] Некому записать гибель '{hero_name}': досье боя '{battle_id}' нет."
            )
            return
        dossier.add_slain_hero(hero_name)

    # ==================================================================
    # ФОНОВЫЕ СЛУХИ
    # ==================================================================

    async def speak_rumor(
        self, world_state: WorldState, faction_id: Optional[str] = None
    ) -> Optional[RumorEntry]:
        """
        Роняет слух в окно логов, если боев не было достаточно долго.
        """
        if self._rumors is None:
            return None
        if not self._rumors.should_speak(world_state):
            return None

        faction = self._resolve_faction(world_state, faction_id)
        rumor = await self._rumors.generate_rumor(world_state, faction)
        if rumor is None:
            return None

        await self._archive.record_rumor(world_state, rumor)

        # сбрасываем таймер или откатываем его, чтобы слухи не генерировались каждый такт
        world_state.ticks_since_last_battle = 0

        return rumor

    # ==================================================================
    # ВИТРИНА ДЛЯ ИНТЕРФЕЙСА
    # ==================================================================

    def get_history(
        self, world_state: WorldState, limit: int = CHRONICLE_HISTORY_PAGE_SIZE
    ) -> list[ChronicleEntry]:
        return self._archive.get_entries(world_state, limit=limit)

    def get_fallen(
        self, world_state: WorldState, limit: int = CHRONICLE_HISTORY_PAGE_SIZE
    ) -> list[FallenRecord]:
        return self._hall.get_records(world_state, limit=limit)

    def get_rumors(
        self, world_state: WorldState, limit: int = CHRONICLE_HISTORY_PAGE_SIZE
    ) -> list[RumorEntry]:
        return self._archive.get_rumors(world_state, limit=limit)

    async def get_archived_history(
        self, limit: int = CHRONICLE_HISTORY_PAGE_SIZE
    ) -> list[dict[str, Any]]:
        """Летописи прошлых партий из базы - для меню вне активной игры."""
        return await self._archive.get_persisted_entries(limit=limit)

    async def get_archived_fallen(
        self, limit: int = CHRONICLE_HISTORY_PAGE_SIZE
    ) -> list[dict[str, Any]]:
        """Павшие прошлых партий из базы."""
        return await self._hall.get_persisted_records(limit=limit)

    # ==================================================================
    # ПОРОГ ЗНАЧИМОСТИ
    # ==================================================================

    def is_chronicle_worthy(self, dossier: BattleDossier) -> bool:
        """
        Достоин ли бой летописи (см. docs/game_mechanics/chronicler.md).

        Летопись - редкое событие: штурм цитадели, крупное сражение или
        гибель кого-то, у кого было имя. Мелкие стычки на дорогах остаются
        строчкой в логах.
        """
        if dossier.is_siege:
            return True
        if dossier.heroes_slain or dossier.named_squads_lost:
            return True
        return dossier.min_squads_per_side >= CHRONICLE_MIN_SQUADS_PER_SIDE

    # ==================================================================
    # ВНУТРЕННЯЯ ЛОГИКА
    # ==================================================================

    async def _write_chronicle(
        self, world_state: WorldState, dossier: BattleDossier
    ) -> Optional[ChronicleEntry]:
        """
        Просит модель пересказать бой и кладет страницу в летопись.
        """
        if self._chronicles is None:
            return None
        if self._archive.has_entry(world_state, dossier.battle_id):
            return None

        faction = self._viewpoint_faction(world_state, dossier)
        context = self._collector.render_context(dossier)

        try:
            response = await self._chronicles.generate_chronicle(
                dossier=dossier, battle_context=context, faction=faction
            )
        except ChronicleGenerationFailedError as error:
            main_logger.error(f"[Chronicler] {error.message}")
            return None

        entry = ChronicleEntry.from_response(
            response,
            battle_id=dossier.battle_id,
            tick=world_state.time.total_ticks,
            location_name=dossier.location_name,
            faction_id=faction.id if faction is not None else None,
        )
        await self._archive.record_battle(world_state, entry)
        return entry

    async def _bury_named_squads(
        self, world_state: WorldState, dossier: BattleDossier
    ) -> list[FallenRecord]:
        """
        Пишет некрологи всем именным отрядам, полегшим в этом бою.
        """
        if self._chronicles is None:
            return []

        context = self._collector.render_context(dossier)
        buried: list[FallenRecord] = []

        for squad_log in dossier.named_squads_lost:
            if self._hall.is_buried(world_state, squad_log.squad_id):
                continue

            subject = FallenSubject.from_squad_log(
                squad_log, killer_name=self._killer_of(dossier, squad_log.side)
            )

            try:
                response = await self._chronicles.generate_epitaph(
                    subject=subject,
                    dossier=dossier,
                    battle_context=context,
                    faction=self._faction_of(world_state, squad_log.faction_id),
                )
            except ChronicleGenerationFailedError as error:
                main_logger.error(f"[Chronicler] {error.message}")
                continue

            record = FallenRecord.from_response(
                response,
                subject=subject,
                death_tick=world_state.time.total_ticks,
                battle_id=dossier.battle_id,
            )
            await self._hall.bury(world_state, record)
            buried.append(record)

        return buried

    def _viewpoint_faction(
        self, world_state: WorldState, dossier: BattleDossier
    ) -> Optional[Faction]:
        """
        Чьими глазами написана страница.

        Летопись читает игрок, поэтому его фракция имеет приоритет: свиток
        должен быть выдержан в его культуре. Если игрок в бою не участвовал -
        пишет победитель, а за неимением победителя - нападавшая сторона.
        """
        candidates = [dossier.attacker_faction_id, dossier.defender_faction_id]

        player = world_state.get_player_faction()
        if player is not None and player.id in candidates:
            return player

        for faction_id in (dossier.victor_faction_id, *candidates):
            faction = self._faction_of(world_state, faction_id)
            if faction is not None:
                return faction
        return None

    def _killer_of(self, dossier: BattleDossier, side: BattleSide) -> str:
        """
        Кто вырезал отряд: противоположная сторона боя.

        Точного убийцу тактические отчеты не сохраняют, поэтому в надгробии
        стоит фракция врага - этого хватает и летописцу, и интерфейсу.
        """
        enemy_id = (
            dossier.defender_faction_id
            if side == BattleSide.ATTACKER
            else dossier.attacker_faction_id
        )
        return enemy_id or ""

    def _resolve_faction(
        self, world_state: WorldState, faction_id: Optional[str]
    ) -> Optional[Faction]:
        """
        Фракция по идентификатору, а без него - фракция игрока.
        """
        if faction_id is None:
            return world_state.get_player_faction()
        return world_state.get_faction(faction_id)

    def _faction_of(
        self, world_state: WorldState, faction_id: Optional[str]
    ) -> Optional[Faction]:
        if faction_id is None:
            return None
        return world_state.get_faction(faction_id)
