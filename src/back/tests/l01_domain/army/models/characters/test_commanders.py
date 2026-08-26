"""
Тесты для src/back/l01_domain/army/models/characters/commanders.py
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.army.models.characters.commanders import (
    Commander,
    CommanderCharacteristics,
    CommanderGenerationType,
    CommanderState,
    CommanderTrait,
)
from src.back.l01_domain.common import MechanicalModifier, StatName
from src.back.l01_domain.exceptions.army import NegativeExperienceError


@pytest.fixture
def cynic_trait() -> CommanderTrait:
    return CommanderTrait(
        id="trait_card_player",
        name="Игрок в карты",
        text_fragment="Ты обожаешь азартные метафоры и рискованные тактики.",
    )


@pytest.fixture
def procedural_commander(cynic_trait) -> Commander:
    return Commander(
        name="Тестовый Полководец",
        faction_id="humans",
        role_title="Стратег",
        generation_type=CommanderGenerationType.PROCEDURAL,
        traits=[cynic_trait],
    )


class TestCommanderTrait:
    def test_modifier_is_optional(self, cynic_trait):
        assert cynic_trait.modifier is None

    def test_trait_can_carry_a_mechanical_modifier(self):
        trait = CommanderTrait(
            id="trait_craven",
            name="Труслив",
            text_fragment="Ты избегаешь прямых столкновений любой ценой.",
            modifier=MechanicalModifier(stat_name=StatName.AMBUSH_RESISTANCE, value=-0.1),
        )

        assert trait.modifier is not None
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
    def test_each_commander_gets_a_unique_id(self, cynic_trait):
        first = Commander(
            name="Первый",
            faction_id="humans",
            generation_type=CommanderGenerationType.PROCEDURAL,
            traits=[cynic_trait],
        )
        second = Commander(
            name="Второй",
            faction_id="humans",
            generation_type=CommanderGenerationType.PROCEDURAL,
            traits=[cynic_trait],
        )

        assert first.id != second.id

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

    def test_legendary_commander_can_carry_fixed_equipment(self, cynic_trait):
        commander = Commander(
            name='Гром "Железное брюхо"',
            faction_id="greenskins",
            role_title="Вождь",
            generation_type=CommanderGenerationType.LEGENDARY,
            traits=[cynic_trait],
            is_legendary=True,
            legendary_prompt_ref="prompt/GREENSKINS/COMMANDERS/LEGENDARY/GROM.md",
            fixed_equipment_ids=["cannonball_stuck_in_belly"],
        )

        assert commander.is_legendary is True
        assert "cannonball_stuck_in_belly" in commander.fixed_equipment_ids
