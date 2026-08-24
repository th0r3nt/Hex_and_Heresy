"""
Тесты для src/back/l01_domain/world/models/battle_log.py

Досье боя - источник всех чисел, которые летописец пересказывает словами,
поэтому проверяем именно арифметику: потери, доли, масштаб и признак резни.
"""

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.world.models.battle_log import (
    BattleDossier,
    BattleSide,
    BattleTurningPoint,
    SquadBattleLog,
    TurningPointKind,
)


def _make_log(
    squad_id: str,
    side: BattleSide,
    initial_count: int = 100,
    is_named: bool = False,
) -> SquadBattleLog:
    return SquadBattleLog(
        squad_id=squad_id,
        display_name=f"Отряд {squad_id}",
        archetype_name="Ополчение",
        is_named=is_named,
        race=FactionRace.HUMANS,
        side=side,
        initial_count=initial_count,
    )


def _make_dossier(attackers: int = 2, defenders: int = 2, units: int = 100) -> BattleDossier:
    dossier = BattleDossier(battle_id="battle_1")
    for i in range(attackers):
        dossier.register_squad(_make_log(f"atk_{i}", BattleSide.ATTACKER, units))
    for i in range(defenders):
        dossier.register_squad(_make_log(f"def_{i}", BattleSide.DEFENDER, units))
    return dossier


class TestSquadBattleLog:
    def test_survivors_and_loss_ratio(self):
        log = _make_log("atk_0", BattleSide.ATTACKER, initial_count=80)
        log.deaths = 20

        assert log.survivors == 60
        assert log.loss_ratio == 0.25

    def test_loss_ratio_never_exceeds_one(self):
        """Перебор потерь над численностью не должен ломать долю."""
        log = _make_log("atk_0", BattleSide.ATTACKER, initial_count=10)
        log.deaths = 15

        assert log.loss_ratio == 1.0
        assert log.survivors == 0

    def test_empty_squad_has_no_losses(self):
        log = _make_log("atk_0", BattleSide.ATTACKER, initial_count=0)

        assert log.loss_ratio == 0.0
        assert log.survivors == 0


class TestBattleDossierAccumulation:
    def test_deaths_accumulate_and_mark_wipe_out(self):
        dossier = _make_dossier(units=50)

        dossier.add_deaths("atk_0", 20)
        dossier.add_deaths("atk_0", 30)

        log = dossier.get_squad("atk_0")
        assert log is not None
        assert log.deaths == 50
        assert log.wiped_out is True

    def test_partial_losses_do_not_wipe_squad(self):
        dossier = _make_dossier(units=50)

        dossier.add_deaths("atk_0", 49)

        log = dossier.get_squad("atk_0")
        assert log is not None
        assert log.wiped_out is False

    def test_unknown_squad_is_ignored(self):
        """Подкрепление, не заведенное в досье, не должно ронять накопление."""
        dossier = _make_dossier()

        dossier.add_deaths("stranger", 10)
        dossier.add_kills("stranger", 10)
        dossier.mark_panic("stranger")

        assert dossier.total_deaths == 0

    def test_register_squad_keeps_initial_snapshot(self):
        """Повторная регистрация не переписывает исходную численность."""
        dossier = BattleDossier(battle_id="battle_1")
        dossier.register_squad(_make_log("atk_0", BattleSide.ATTACKER, initial_count=100))
        dossier.add_deaths("atk_0", 40)

        dossier.register_squad(_make_log("atk_0", BattleSide.ATTACKER, initial_count=60))

        log = dossier.get_squad("atk_0")
        assert log is not None
        assert log.initial_count == 100
        assert log.deaths == 40

    def test_non_positive_amounts_are_ignored(self):
        dossier = _make_dossier()

        dossier.add_deaths("atk_0", 0)
        dossier.add_kills("atk_0", -5)

        log = dossier.get_squad("atk_0")
        assert log is not None
        assert log.deaths == 0
        assert log.kills == 0

    def test_slain_heroes_are_deduplicated(self):
        dossier = _make_dossier()

        dossier.add_slain_hero("Гром Железное брюхо")
        dossier.add_slain_hero("Гром Железное брюхо")
        dossier.add_slain_hero("")

        assert dossier.heroes_slain == ["Гром Железное брюхо"]

    def test_turning_points_keep_order(self):
        dossier = _make_dossier()

        dossier.add_turning_point(
            BattleTurningPoint(tick=1, kind=TurningPointKind.CHARGE_BROKE_LINE)
        )
        dossier.add_turning_point(BattleTurningPoint(tick=3, kind=TurningPointKind.CHAIN_PANIC))

        assert [tp.kind for tp in dossier.turning_points] == [
            TurningPointKind.CHARGE_BROKE_LINE,
            TurningPointKind.CHAIN_PANIC,
        ]


class TestBattleDossierSummary:
    def test_side_counts_and_totals(self):
        dossier = _make_dossier(attackers=2, defenders=3, units=100)

        dossier.add_deaths("atk_0", 50)
        dossier.add_deaths("def_0", 100)
        dossier.add_deaths("def_1", 20)

        assert dossier.side_initial_count(BattleSide.ATTACKER) == 200
        assert dossier.side_initial_count(BattleSide.DEFENDER) == 300
        assert dossier.side_deaths(BattleSide.DEFENDER) == 120
        assert dossier.side_loss_ratio(BattleSide.ATTACKER) == 0.25
        assert dossier.total_deaths == 170

    def test_min_squads_per_side_measures_scale(self):
        dossier = _make_dossier(attackers=7, defenders=2)

        assert dossier.min_squads_per_side == 2

    def test_massacre_when_one_side_is_almost_wiped(self):
        dossier = _make_dossier(attackers=2, defenders=2, units=100)

        dossier.add_deaths("def_0", 100)
        dossier.add_deaths("def_1", 60)

        assert dossier.side_loss_ratio(BattleSide.DEFENDER) == 0.8
        assert dossier.is_massacre is True

    def test_even_battle_is_not_massacre(self):
        dossier = _make_dossier(units=100)

        dossier.add_deaths("atk_0", 30)
        dossier.add_deaths("def_0", 30)

        assert dossier.is_massacre is False

    def test_named_squads_lost_only_counts_wiped_veterans(self):
        dossier = BattleDossier(battle_id="battle_1")
        dossier.register_squad(_make_log("atk_0", BattleSide.ATTACKER, 50, is_named=True))
        dossier.register_squad(_make_log("atk_1", BattleSide.ATTACKER, 50, is_named=True))
        dossier.register_squad(_make_log("def_0", BattleSide.DEFENDER, 50))

        dossier.add_deaths("atk_0", 50)  # именной полег
        dossier.add_deaths("atk_1", 10)  # именной выжил
        dossier.add_deaths("def_0", 50)  # безымянный полег

        lost = dossier.named_squads_lost
        assert [log.squad_id for log in lost] == ["atk_0"]

    def test_finished_flag_follows_finished_tick(self):
        dossier = _make_dossier()

        assert dossier.is_finished is False

        dossier.finished_tick = 7
        assert dossier.is_finished is True
