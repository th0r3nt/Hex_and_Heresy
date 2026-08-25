"""
Сбор числового лога боя и его рендер в контекст для языковой модели.

Тактические отчеты (TacticalTurnReport) живут один раунд и оперируют
идентификаторами: по ним нельзя рассказать историю - к финалу боя выбитый
отряд уже не найти в мире, а его имя нигде не останется. Коллектор копит
досье с первого раунда: кто вышел на поле, сколько их было, что переломило
сражение.

Здесь нет ни одного обращения к LLM: это чистая математика, которую можно
гонять в тестах без сети.
"""

from typing import Optional

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.combat.constants import FacingAngle, ReactionType
from src.back.l01_domain.combat.models.reports import TacticalTurnReport
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.exceptions.chronicler import BattleDossierNotFoundError
from src.back.l01_domain.maps.constants import ALLIED_LANDS_RING_RADIUS
from src.back.l01_domain.maps.models.strategic import HexCoordinates, hex_distance
from src.back.l01_domain.world.battle_summary import render_battle_summary
from src.back.l01_domain.world.constants import CHRONICLE_CHAIN_PANIC_SQUADS
from src.back.l01_domain.world.models.battle_log import (
    BattleDossier,
    BattleSide,
    BattleTurningPoint,
    SquadBattleLog,
    TurningPointKind,
)
from src.back.l01_domain.world.models.state import WorldState

# Во сколько раз потери защитника должны превысить потери атакующего,
# чтобы натиск считался сломавшим строй
CHARGE_BROKEN_LINE_RATIO = 3.0


def describe_location(world_state: WorldState, coordinates: Optional[HexCoordinates]) -> str:
    """
    Дает бою имя места.

    Гексы на карте безымянные, поэтому название собирается из того, чьи это
    земли: цитадель, ее окрестности или ничья земля с координатами.
    """
    if coordinates is None:
        return "Неизвестные земли"

    q, r = coordinates.to_axial()

    for faction in world_state.factions.values():
        if faction.capital_hex is None:
            continue
        distance = hex_distance(coordinates, faction.capital_hex)
        if distance == 0:
            return f"Цитадель фракции «{faction.name}»"
        if distance <= ALLIED_LANDS_RING_RADIUS:
            return f"Окрестности цитадели «{faction.name}» ({q}, {r})"

    return f"Ничья земля ({q}, {r})"


def is_capital_hex(world_state: WorldState, coordinates: Optional[HexCoordinates]) -> bool:
    """Стоит ли бой на цитадели: штурм базы идет в летопись всегда."""
    if coordinates is None:
        return False
    return any(
        faction.capital_hex is not None and faction.capital_hex == coordinates
        for faction in world_state.factions.values()
    )


class BattleLogCollector:
    """
    Ведет досье незавершенных боев: заводит их на старте, копит числа по
    раундам и закрывает по завершении сражения.

    Досье живет в памяти сервиса, а не в WorldState: сохраняться посреди
    тактического боя игре все равно запрещено (SaveDuringBattleForbiddenError).
    """

    def __init__(self) -> None:
        self._dossiers: dict[str, BattleDossier] = {}

    # ==================================================================
    # ЖИЗНЕННЫЙ ЦИКЛ ДОСЬЕ
    # ==================================================================

    def start_battle(
        self,
        world_state: WorldState,
        battle_state: TacticalBattleState,
        squads: dict[str, Squad],
        strategic_hex: Optional[HexCoordinates] = None,
    ) -> BattleDossier:
        """
        Заводит досье боя, снимая состав сторон и обстановку до первого залпа.

        Повторный вызов на тот же бой возвращает уже заведенное досье:
        оркестратор может сообщить о начале боя не один раз, а исходную
        численность переписывать нельзя.
        """
        existing = self._dossiers.get(battle_state.id)
        if existing is not None:
            return existing

        faction_by_squad = self._map_squads_to_factions(world_state)

        dossier = BattleDossier(
            battle_id=battle_state.id,
            started_tick=world_state.time.total_ticks,
            location_name=describe_location(world_state, strategic_hex),
            weather=battle_state.weather,
            time_of_day=battle_state.time_of_day,
            is_siege=is_capital_hex(world_state, strategic_hex),
        )

        for side, squad_ids in (
            (BattleSide.ATTACKER, battle_state.attacker_squad_ids),
            (BattleSide.DEFENDER, battle_state.defender_squad_ids),
        ):
            for squad_id in squad_ids:
                squad = squads.get(squad_id)
                if squad is None:
                    continue
                dossier.register_squad(
                    self._snapshot_squad(squad, side, faction_by_squad.get(squad_id))
                )

        dossier.attacker_faction_id = self._dominant_faction(dossier, BattleSide.ATTACKER)
        dossier.defender_faction_id = self._dominant_faction(dossier, BattleSide.DEFENDER)

        self._dossiers[dossier.battle_id] = dossier
        return dossier

    def get_dossier(self, battle_id: str) -> Optional[BattleDossier]:
        return self._dossiers.get(battle_id)

    def require_dossier(self, battle_id: str) -> BattleDossier:
        dossier = self._dossiers.get(battle_id)
        if dossier is None:
            raise BattleDossierNotFoundError(battle_id)
        return dossier

    def discard(self, battle_id: str) -> Optional[BattleDossier]:
        """
        Выкидывает досье из памяти. Вызывается после того, как летопись
        написана: держать закрытые бои коллектору незачем.
        """
        return self._dossiers.pop(battle_id, None)

    # ==================================================================
    # НАКОПЛЕНИЕ РАУНДОВ
    # ==================================================================

    def absorb_turn(self, report: TacticalTurnReport) -> BattleDossier:
        """
        Разбирает отчет одного раунда: разносит потери и убийства по отрядам
        и выцепляет переломные моменты.

        Сами отряды сюда не нужны - все, что о них важно знать, снято в
        досье на старте боя. Арифметика потерь повторяет
        TacticalTurnOrchestrator: оба считают по одним и тем же отчетам,
        поэтому расхождения между летописью и механикой быть не может.

        Повторный отчет того же раунда игнорируется: последний раунд боя
        приезжает дважды - и как завершенный раунд, и как конец сражения.
        """
        dossier = self.require_dossier(report.battle_id)

        if report.tick <= dossier.last_absorbed_tick:
            return dossier
        dossier.last_absorbed_tick = report.tick

        wiped_before = {
            squad_id for squad_id, log in dossier.squads.items() if log.wiped_out
        }

        self._absorb_charges(dossier, report)
        self._absorb_ranged(dossier, report)
        self._absorb_melee(dossier, report)
        self._absorb_morale(dossier, report)
        self._detect_wipe_outs(dossier, report, wiped_before)

        return dossier

    def finalize(self, report: TacticalTurnReport) -> BattleDossier:
        """
        Закрывает досье последним отчетом боя: фиксирует победителя и раунд,
        на котором все кончилось.

        Последний раунд тоже идет в накопление - именно в нем обычно и
        случается развязка.
        """
        dossier = self.absorb_turn(report)
        dossier.finished_tick = report.tick
        dossier.victor_faction_id = report.victor_faction_id
        return dossier

    # ==================================================================
    # РЕНДЕР КОНТЕКСТА ДЛЯ LLM
    # ==================================================================

    def render_context(self, dossier: BattleDossier) -> str:
        """
        Разворачивает досье в текстовую сводку для user_prompt.

        Сам текст собирает домен (world/battle_summary.py): та же сводка
        нужна сборщику контекста промптов, и расходиться они не должны.
        """
        return render_battle_summary(dossier)

    # ==================================================================
    # РАЗБОР ОТЧЕТОВ
    # ==================================================================

    def _absorb_charges(self, dossier: BattleDossier, report: TacticalTurnReport) -> None:
        for charge in report.charge_reports:
            dossier.add_deaths(charge.attacker_squad_id, charge.attacker_deaths)
            dossier.add_deaths(charge.defender_squad_id, charge.defender_deaths)
            dossier.add_kills(charge.attacker_squad_id, charge.defender_deaths)
            dossier.add_kills(charge.defender_squad_id, charge.attacker_deaths)

            if self._is_line_broken(charge.reaction, charge.attacker_deaths, charge.defender_deaths):
                dossier.add_turning_point(
                    BattleTurningPoint(
                        tick=report.tick,
                        kind=TurningPointKind.CHARGE_BROKE_LINE,
                        actor_name=self._name_of(dossier, charge.attacker_squad_id),
                        target_name=self._name_of(dossier, charge.defender_squad_id),
                        value=float(charge.defender_deaths),
                        details=(
                            "защитники не приняли удар и побежали"
                            if charge.reaction == ReactionType.FLEE
                            else "строй смяли одним натиском"
                        ),
                    )
                )

    def _absorb_ranged(self, dossier: BattleDossier, report: TacticalTurnReport) -> None:
        for shot in report.ranged_reports:
            dossier.add_kills(shot.attacker_squad_id, shot.kills)

            if shot.friendly_fire_squad_id:
                dossier.add_deaths(shot.friendly_fire_squad_id, shot.friendly_fire_kills)
            elif shot.target_squad_id:
                dossier.add_deaths(shot.target_squad_id, shot.kills)

            if shot.is_misfire or shot.friendly_fire_kills > 0:
                dossier.add_turning_point(
                    BattleTurningPoint(
                        tick=report.tick,
                        kind=TurningPointKind.MISFIRE,
                        actor_name=self._name_of(dossier, shot.attacker_squad_id),
                        target_name=self._name_of(dossier, shot.friendly_fire_squad_id),
                        value=float(shot.friendly_fire_kills),
                        details=(
                            "залп ушел по своим"
                            if shot.friendly_fire_kills > 0
                            else "оружие дало осечку"
                        ),
                    )
                )

    def _absorb_melee(self, dossier: BattleDossier, report: TacticalTurnReport) -> None:
        for melee in report.melee_reports:
            dossier.add_deaths(melee.defender_squad_id, melee.kills)
            dossier.add_kills(melee.attacker_squad_id, melee.kills)

            if melee.flank_angle != FacingAngle.FRONT and melee.kills > 0:
                dossier.add_turning_point(
                    BattleTurningPoint(
                        tick=report.tick,
                        kind=TurningPointKind.FLANK_SLAUGHTER,
                        actor_name=self._name_of(dossier, melee.attacker_squad_id),
                        target_name=self._name_of(dossier, melee.defender_squad_id),
                        value=float(melee.kills),
                        details=(
                            "удар в тыл"
                            if melee.flank_angle == FacingAngle.REAR
                            else "удар во фланг"
                        ),
                    )
                )

    def _absorb_morale(self, dossier: BattleDossier, report: TacticalTurnReport) -> None:
        morale = report.morale_report

        for squad_id in morale.panicking_squad_ids:
            dossier.mark_panic(squad_id)

        panicked_count = len(morale.panicking_squad_ids)
        if morale.chain_panic_shocks or panicked_count >= CHRONICLE_CHAIN_PANIC_SQUADS:
            names = [
                name
                for name in (
                    self._name_of(dossier, squad_id)
                    for squad_id in morale.panicking_squad_ids
                )
                if name
            ]
            dossier.add_turning_point(
                BattleTurningPoint(
                    tick=report.tick,
                    kind=TurningPointKind.CHAIN_PANIC,
                    actor_name=names[0] if names else None,
                    value=float(panicked_count),
                    details="бегство перекинулось на соседей: " + ", ".join(names)
                    if names
                    else "строй посыпался",
                )
            )

        for cell in morale.new_corpse_piles:
            dossier.add_turning_point(
                BattleTurningPoint(
                    tick=report.tick,
                    kind=TurningPointKind.CORPSE_PILE,
                    value=0.0,
                    details=f"на клетке ({cell.x}, {cell.y}) выросла гора трупов",
                )
            )

    def _detect_wipe_outs(
        self,
        dossier: BattleDossier,
        report: TacticalTurnReport,
        wiped_before: set[str],
    ) -> None:
        """
        Отмечает отряды, которых не стало именно в этом раунде.
        """
        for squad_id, log in dossier.squads.items():
            if not log.wiped_out or squad_id in wiped_before:
                continue
            dossier.add_turning_point(
                BattleTurningPoint(
                    tick=report.tick,
                    kind=TurningPointKind.SQUAD_WIPED_OUT,
                    target_name=log.display_name,
                    value=float(log.initial_count),
                    details=(
                        "именной отряд полег до последнего бойца"
                        if log.is_named
                        else "отряд выбит подчистую"
                    ),
                )
            )

    # ==================================================================
    # СЛУЖЕБНОЕ
    # ==================================================================

    def _snapshot_squad(
        self, squad: Squad, side: BattleSide, faction_id: Optional[str]
    ) -> SquadBattleLog:
        return SquadBattleLog(
            squad_id=squad.id,
            display_name=squad.display_name,
            archetype_name=squad.archetype.name,
            is_named=squad.veterancy.is_named,
            commander_name=squad.veterancy.commander_name,
            faction_id=faction_id or squad.archetype.faction_id,
            race=squad.archetype.race,
            side=side,
            initial_count=squad.state.unit_count,
        )

    def _map_squads_to_factions(self, world_state: WorldState) -> dict[str, str]:
        """
        Строит карту squad_id -> faction_id по армиям мира.

        Архетип отряда знает свою расу, но не всегда владельца: наемники
        воюют под чужим знаменем, поэтому источник истины - армия.
        """
        mapping: dict[str, str] = {}
        for army in world_state.armies.values():
            for squad in army.squads:
                mapping[squad.id] = army.faction_id
        return mapping

    def _dominant_faction(
        self, dossier: BattleDossier, side: BattleSide
    ) -> Optional[str]:
        """
        Чья это сторона: фракция, выставившая больше всех карточек.
        """
        counts: dict[str, int] = {}
        for log in dossier.side_squads(side):
            if log.faction_id is None:
                continue
            counts[log.faction_id] = counts.get(log.faction_id, 0) + 1

        if not counts:
            return None
        return max(counts.items(), key=lambda item: item[1])[0]

    def _is_line_broken(
        self, reaction: ReactionType, attacker_deaths: int, defender_deaths: int
    ) -> bool:
        if reaction == ReactionType.FLEE:
            return True
        if defender_deaths <= 0:
            return False
        # Атакующий мог не потерять никого: тогда планку задает сам множитель,
        # иначе одна случайная смерть защитника читалась бы как смятый строй
        return defender_deaths >= CHARGE_BROKEN_LINE_RATIO * max(1, attacker_deaths)

    def _name_of(self, dossier: BattleDossier, squad_id: Optional[str]) -> Optional[str]:
        if squad_id is None:
            return None
        log = dossier.get_squad(squad_id)
        return log.display_name if log is not None else None
