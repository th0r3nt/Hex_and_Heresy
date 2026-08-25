"""
Тесты для src/back/l01_domain/army/models/characters/commanders.py
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.common import MechanicalModifier, StatName
from src.back.l01_domain.army.models.characters.commanders import (
    Commander,
    CommanderArchetype,
    CommanderArchetypeStats,
    CommanderCharacteristics,
    CommanderGenerationType,
    CommanderState,
    CommanderTrait,
)

from src.back.l01_domain.exceptions.army import NegativeExperienceError


@pytest.fixture
def strategist_archetype() -> CommanderArchetype:
    return CommanderArchetype(
        id="archetype_strategist",
        name="Стратег",
        description="+1 к дальности перемещения, штраф к урону в ближнем бою.",
        stats=CommanderArchetypeStats(
            strategic_map_range_bonus=1,
            melee_damage_modifier=-0.1,
        ),
    )


@pytest.fixture
def cynic_trait() -> CommanderTrait:
    return CommanderTrait(
        id="trait_card_player",
        name="Игрок в карты",
        text_fragment="Ты обожаешь азартные метафоры и рискованные тактики.",
    )


@pytest.fixture
def procedural_commander(strategist_archetype, cynic_trait) -> Commander:
    return Commander(
        name="Тестовый Полководец",
        faction_id="humans",
        generation_type=CommanderGenerationType.PROCEDURAL,
        archetype=strategist_archetype,
        trait=cynic_trait,
    )


class TestCommanderArchetypeStats:
    def test_defaults_are_neutral(self):
        stats = CommanderArchetypeStats()

        assert stats.strategic_map_range_bonus == 0
        assert stats.melee_damage_modifier == 0.0
        assert stats.upkeep_gold_modifier == 1.0

    def test_ambush_resistance_is_bounded(self):
        with pytest.raises(ValidationError):
            CommanderArchetypeStats(ambush_resistance_modifier=1.5)

    def test_upkeep_modifier_must_be_positive(self):
        with pytest.raises(ValidationError):
            CommanderArchetypeStats(upkeep_gold_modifier=0)

    def test_is_frozen(self):
        stats = CommanderArchetypeStats()

        with pytest.raises(ValidationError):
            stats.strategic_map_range_bonus = 5


class TestCommanderTrait:
    def test_modifier_is_optional(self, cynic_trait):
        assert cynic_trait.modifier is None

    def test_trait_can_carry_a_mechanical_modifier(self):
        # "Труслив" - не только нарративная черта, но и числовой эффект.
        trait = CommanderTrait(
            id="trait_craven",
            name="Труслив",
            text_fragment="Ты избегаешь прямых столкновений любой ценой.",
            modifier=MechanicalModifier(stat_name=StatName.AMBUSH_RESISTANCE, value=-0.1),
        )

        assert trait.modifier.stat_name == StatName.AMBUSH_RESISTANCE


class TestCommanderCharacteristics:
    def test_defaults(self):
        characteristics = CommanderCharacteristics()

        assert characteristics.authority == 10
        assert characteristics.tactical_acumen == 10
        assert characteristics.resilience == 10
        assert characteristics.cunning == 10

    @pytest.mark.parametrize("value", [-1, 101])
    def test_authority_must_stay_within_0_100(self, value):
        with pytest.raises(ValidationError):
            CommanderCharacteristics(authority=value)


class TestCommanderState:
    def test_defaults(self):
        state = CommanderState()

        assert state.experience == 0
        assert state.level == 1
        assert state.is_alive is True
        assert state.army_id is None


class TestCommander:
    def test_each_commander_gets_a_unique_id(self, strategist_archetype, cynic_trait):
        first = Commander(
            name="Первый",
            faction_id="humans",
            generation_type=CommanderGenerationType.PROCEDURAL,
            archetype=strategist_archetype,
            trait=cynic_trait,
        )
        second = Commander(
            name="Второй",
            faction_id="humans",
            generation_type=CommanderGenerationType.PROCEDURAL,
            archetype=strategist_archetype,
            trait=cynic_trait,
        )

        assert first.id != second.id

    def test_upkeep_multiplier_mirrors_archetype(self, procedural_commander):
        assert (
            procedural_commander.upkeep_gold_multiplier
            == procedural_commander.archetype.stats.upkeep_gold_modifier
        )

    def test_gain_experience_accumulates(self, procedural_commander):
        procedural_commander.gain_experience(50)
        procedural_commander.gain_experience(25)

        assert procedural_commander.state.experience == 75

    def test_gain_experience_rejects_negative_amount(self, procedural_commander):
        with pytest.raises(NegativeExperienceError):
            procedural_commander.gain_experience(-10)

    def test_assign_and_unassign_army(self, procedural_commander):
        procedural_commander.assign_to_army("army_42")
        assert procedural_commander.state.army_id == "army_42"

        procedural_commander.unassign_from_army()
        assert procedural_commander.state.army_id is None

    def test_legendary_defaults_are_off_for_procedural_commanders(self, procedural_commander):
        assert procedural_commander.is_legendary is False
        assert procedural_commander.legendary_prompt_ref is None
        assert procedural_commander.fixed_equipment_ids == []

    def test_legendary_commander_can_carry_fixed_equipment(
        self, strategist_archetype, cynic_trait
    ):
        # Как Гром "Железное брюхо" с несъёмным пушечным ядром в животе.
        commander = Commander(
            name='Гром "Железное брюхо"',
            faction_id="greenskins",
            generation_type=CommanderGenerationType.LEGENDARY,
            archetype=strategist_archetype,
            trait=cynic_trait,
            is_legendary=True,
            legendary_prompt_ref="prompt/GREENSKINS/COMMANDERS/LEGENDARY/GROM.md",
            fixed_equipment_ids=["cannonball_stuck_in_belly"],
        )

        assert commander.is_legendary is True
        assert "cannonball_stuck_in_belly" in commander.fixed_equipment_ids
