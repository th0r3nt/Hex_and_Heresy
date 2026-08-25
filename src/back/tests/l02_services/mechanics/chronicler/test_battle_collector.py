"""
Тесты сбора числового лога боя (generation/battles.py).

Летописец врет только в художественной части: числа в его сводке обязаны
сходиться с тактическими отчетами до единицы.
"""

import pytest

from src.back.l01_domain.combat.constants import FacingAngle, ReactionType
from src.back.l01_domain.combat.models.reports import (
    ChargeStepReport,
    MeleeCombatReport,
    MoraleAndEnvironmentReport,
    RangedCombatReport,
)
from src.back.l01_domain.exceptions.chronicler import BattleDossierNotFoundError
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.maps.models.tactical import CellCoordinates
from src.back.l01_domain.world.models.battle_log import BattleSide, TurningPointKind
from src.back.l02_services.mechanics.chronicler.generation.battles import (
    BattleLogCollector,
    describe_location,
)


@pytest.fixture
def collector() -> BattleLogCollector:
    return BattleLogCollector()


@pytest.fixture
def dossier(collector, world, battle_state, battle_squads, battle_hex):
    return collector.start_battle(world, battle_state, battle_squads, battle_hex)


class TestStartBattle:
    def test_snapshots_both_sides(self, dossier):
        assert len(dossier.side_squads(BattleSide.ATTACKER)) == 6
        assert len(dossier.side_squads(BattleSide.DEFENDER)) == 6
        assert dossier.side_initial_count(BattleSide.ATTACKER) == 600

    def test_takes_factions_from_armies(self, dossier):
        assert dossier.attacker_faction_id == "humans"
        assert dossier.defender_faction_id == "greenskins"

    def test_records_setting(self, dossier, world, battle_state):
        assert dossier.started_tick == world.time.total_ticks
        assert dossier.weather == battle_state.weather
        assert dossier.time_of_day == battle_state.time_of_day
        assert dossier.is_siege is False

    def test_siege_is_detected_on_capital_hex(
        self, collector, world, battle_state, battle_squads, humans
    ):
        siege = collector.start_battle(world, battle_state, battle_squads, humans.capital_hex)

        assert siege.is_siege is True
        assert "Цитадель" in siege.location_name

    def test_second_start_keeps_initial_snapshot(
        self, collector, world, battle_state, battle_squads, battle_hex
    ):
        first = collector.start_battle(world, battle_state, battle_squads, battle_hex)
        first.add_deaths("atk_0", 30)

        second = collector.start_battle(world, battle_state, battle_squads, battle_hex)

        assert second is first
        assert second.squads["atk_0"].deaths == 30

    def test_absorb_without_start_is_an_error(self, make_report, collector):
        with pytest.raises(BattleDossierNotFoundError):
            collector.absorb_turn(make_report())


class TestDescribeLocation:
    def test_neutral_hex_carries_coordinates(self, world):
        name = describe_location(world, HexCoordinates.from_axial(4, 0))

        assert name == "Ничья земля (4, 0)"

    def test_capital_is_named_by_faction(self, world, greenskins):
        name = describe_location(world, greenskins.capital_hex)

        assert "Орда Ржавых Клыков" in name

    def test_neighbouring_hex_belongs_to_citadel(self, world, humans):
        neighbour = HexCoordinates.from_axial(1, 0)

        assert "Окрестности" in describe_location(world, neighbour)

    def test_unknown_hex_is_tolerated(self, world):
        assert describe_location(world, None) == "Неизвестные земли"


class TestAbsorbCharges:
    def test_charge_splits_losses_between_sides(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                charge_reports=[
                    ChargeStepReport(
                        attacker_squad_id="atk_0",
                        defender_squad_id="def_0",
                        reaction=ReactionType.ACCEPT_CHARGE,
                        attacker_deaths=5,
                        defender_deaths=12,
                    )
                ]
            )
        )

        assert dossier.squads["atk_0"].deaths == 5
        assert dossier.squads["atk_0"].kills == 12
        assert dossier.squads["def_0"].deaths == 12
        assert dossier.squads["def_0"].kills == 5

    def test_flee_reaction_is_a_broken_line(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                charge_reports=[
                    ChargeStepReport(
                        attacker_squad_id="atk_0",
                        defender_squad_id="def_0",
                        reaction=ReactionType.FLEE,
                        defender_deaths=2,
                    )
                ]
            )
        )

        kinds = [tp.kind for tp in dossier.turning_points]
        assert TurningPointKind.CHARGE_BROKE_LINE in kinds

    def test_even_charge_is_not_a_turning_point(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                charge_reports=[
                    ChargeStepReport(
                        attacker_squad_id="atk_0",
                        defender_squad_id="def_0",
                        reaction=ReactionType.COUNTER_CHARGE,
                        attacker_deaths=10,
                        defender_deaths=12,
                    )
                ]
            )
        )

        assert dossier.turning_points == []

    def test_lopsided_charge_breaks_the_line(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                charge_reports=[
                    ChargeStepReport(
                        attacker_squad_id="atk_0",
                        defender_squad_id="def_0",
                        reaction=ReactionType.ACCEPT_CHARGE,
                        attacker_deaths=2,
                        defender_deaths=30,
                    )
                ]
            )
        )

        point = dossier.turning_points[0]
        assert point.kind == TurningPointKind.CHARGE_BROKE_LINE
        assert point.value == 30.0


class TestAbsorbRanged:
    def test_hits_land_on_the_target(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                ranged_reports=[
                    RangedCombatReport(
                        attacker_squad_id="atk_0",
                        target_cell=CellCoordinates(x=1, y=1),
                        target_squad_id="def_0",
                        kills=7,
                    )
                ]
            )
        )

        assert dossier.squads["def_0"].deaths == 7
        assert dossier.squads["atk_0"].kills == 7

    def test_friendly_fire_kills_own_squad(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                ranged_reports=[
                    RangedCombatReport(
                        attacker_squad_id="atk_0",
                        target_cell=CellCoordinates(x=1, y=1),
                        target_squad_id="def_0",
                        kills=3,
                        is_misfire=True,
                        friendly_fire_kills=4,
                        friendly_fire_squad_id="atk_1",
                    )
                ]
            )
        )

        assert dossier.squads["atk_1"].deaths == 4
        assert dossier.squads["def_0"].deaths == 0
        assert dossier.turning_points[0].kind == TurningPointKind.MISFIRE

    def test_clean_volley_is_not_a_turning_point(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                ranged_reports=[
                    RangedCombatReport(
                        attacker_squad_id="atk_0",
                        target_cell=CellCoordinates(x=1, y=1),
                        target_squad_id="def_0",
                        kills=5,
                    )
                ]
            )
        )

        assert dossier.turning_points == []


class TestAbsorbMelee:
    def test_kills_land_on_the_defender(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                melee_reports=[
                    MeleeCombatReport(
                        attacker_squad_id="atk_0",
                        defender_squad_id="def_0",
                        kills=9,
                    )
                ]
            )
        )

        assert dossier.squads["def_0"].deaths == 9
        assert dossier.squads["atk_0"].kills == 9
        assert dossier.turning_points == []

    def test_rear_attack_is_a_slaughter(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                melee_reports=[
                    MeleeCombatReport(
                        attacker_squad_id="atk_0",
                        defender_squad_id="def_0",
                        kills=9,
                        flank_angle=FacingAngle.REAR,
                    )
                ]
            )
        )

        point = dossier.turning_points[0]
        assert point.kind == TurningPointKind.FLANK_SLAUGHTER
        assert "тыл" in point.details

    def test_bloodless_flanking_is_ignored(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                melee_reports=[
                    MeleeCombatReport(
                        attacker_squad_id="atk_0",
                        defender_squad_id="def_0",
                        kills=0,
                        flank_angle=FacingAngle.FLANK,
                    )
                ]
            )
        )

        assert dossier.turning_points == []


class TestAbsorbMorale:
    def test_panic_is_remembered_on_the_squad(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                morale_report=MoraleAndEnvironmentReport(panicking_squad_ids=["def_0"])
            )
        )

        assert dossier.squads["def_0"].panicked is True

    def test_single_panic_is_not_a_chain(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                morale_report=MoraleAndEnvironmentReport(panicking_squad_ids=["def_0"])
            )
        )

        assert dossier.turning_points == []

    def test_two_panicking_squads_make_a_chain(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                morale_report=MoraleAndEnvironmentReport(
                    panicking_squad_ids=["def_0", "def_1"]
                )
            )
        )

        point = dossier.turning_points[0]
        assert point.kind == TurningPointKind.CHAIN_PANIC
        assert point.value == 2.0

    def test_chain_shock_alone_is_enough(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                morale_report=MoraleAndEnvironmentReport(
                    panicking_squad_ids=["def_0"], chain_panic_shocks={"def_1": 10.0}
                )
            )
        )

        assert dossier.turning_points[0].kind == TurningPointKind.CHAIN_PANIC

    def test_corpse_pile_is_recorded(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                morale_report=MoraleAndEnvironmentReport(
                    new_corpse_piles=[CellCoordinates(x=5, y=6)]
                )
            )
        )

        point = dossier.turning_points[0]
        assert point.kind == TurningPointKind.CORPSE_PILE
        assert "(5, 6)" in point.details


class TestWipeOutDetection:
    def test_wipe_out_is_noticed_once(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                tick=1,
                melee_reports=[
                    MeleeCombatReport(
                        attacker_squad_id="atk_0", defender_squad_id="def_0", kills=100
                    )
                ],
            )
        )
        collector.absorb_turn(
            make_report(
                tick=2,
                melee_reports=[
                    MeleeCombatReport(
                        attacker_squad_id="atk_0", defender_squad_id="def_0", kills=20
                    )
                ],
            )
        )

        wipes = [
            tp for tp in dossier.turning_points if tp.kind == TurningPointKind.SQUAD_WIPED_OUT
        ]
        assert len(wipes) == 1
        assert wipes[0].tick == 1
        assert wipes[0].target_name == "Гоблины"


class TestFinalize:
    def test_last_round_is_absorbed_and_battle_closed(self, make_report, collector, dossier):
        collector.absorb_turn(
            make_report(
                tick=1,
                melee_reports=[
                    MeleeCombatReport(
                        attacker_squad_id="atk_0", defender_squad_id="def_0", kills=40
                    )
                ],
            )
        )

        finalized = collector.finalize(
            make_report(
                tick=2,
                melee_reports=[
                    MeleeCombatReport(
                        attacker_squad_id="atk_0", defender_squad_id="def_0", kills=60
                    )
                ],
                is_battle_finished=True,
                victor_faction_id="humans",
            )
        )

        assert finalized.finished_tick == 2
        assert finalized.victor_faction_id == "humans"
        assert finalized.squads["def_0"].deaths == 100
        assert finalized.is_finished is True

    def test_discard_forgets_the_battle(self, collector, dossier):
        collector.discard(dossier.battle_id)

        assert collector.get_dossier(dossier.battle_id) is None


class TestRenderContext:
    def test_context_carries_numbers_and_names(self, make_report, collector, dossier):
        collector.finalize(
            make_report(
                tick=3,
                charge_reports=[
                    ChargeStepReport(
                        attacker_squad_id="atk_0",
                        defender_squad_id="def_0",
                        reaction=ReactionType.FLEE,
                        defender_deaths=100,
                    )
                ],
                morale_report=MoraleAndEnvironmentReport(
                    panicking_squad_ids=["def_1", "def_2"]
                ),
                is_battle_finished=True,
                victor_faction_id="humans",
            )
        )

        context = collector.render_context(dossier)

        assert "Ничья земля (4, 0)" in context
        assert "Нападавшие (6 карточек" in context
        assert "Оборонявшиеся (6 карточек" in context
        assert "Гоблины" in context
        assert "уничтожен полностью" in context
        assert "бежал с поля" in context
        assert "Переломные моменты:" in context
        assert "humans" in context

    def test_context_of_a_quiet_battle_has_no_turning_points(self, make_report, collector, dossier):
        collector.finalize(make_report(tick=1, is_battle_finished=True))

        context = collector.render_context(dossier)

        assert "Переломные моменты:" not in context
        assert "Победителя нет" in context

    def test_massacre_and_named_losses_are_announced(
        self, collector, world, battle_state, battle_squads, battle_hex
    ):
        battle_squads["def_0"].veterancy.promote(
            commander_name="Гразнык",
            squad_nickname="Клыки Гразныка",
            trait_name="Упрямые",
            lore="...",
        )
        dossier = collector.start_battle(world, battle_state, battle_squads, battle_hex)

        for squad_id in battle_state.defender_squad_ids:
            dossier.add_deaths(squad_id, 100)
        dossier.add_slain_hero("Гром Железное брюхо")

        context = collector.render_context(dossier)

        assert "вырезана почти полностью" in context
        assert "Клыки Гразныка" in context
        assert "Гром Железное брюхо" in context
