"""
Тесты инвариантов полководцев, героев, перков, шрамов и артефактов.
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.army.constants import (
    ArmorCategory,
    EquipmentSlot,
)
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.l01_domain.army.models.characters.artifacts import HeroArtifact
from src.back.l01_domain.army.models.characters.commanders import (
    Commander,
    CommanderArchetype,
    CommanderArchetypeStats,
    CommanderCharacteristics,
    CommanderGenerationType,
    CommanderTrait,
)
from src.back.l01_domain.army.models.characters.heroes import (
    Hero,
    HeroArchetype,
    Perk,
    Scar,
)
from src.back.l01_domain.common import MechanicalModifier
from src.back.l01_domain.exceptions import (
    HeroLevelTooLowError,
    NegativeExperienceError,
)


@pytest.fixture
def sample_hero() -> Hero:
    archetype = HeroArchetype(
        id="arch_warrior",
        name="Воин",
        description="...",
        special_rule="Ярость",
        trigger_modifier=MechanicalModifier(stat_name="damage", value=5.0),
    )
    return Hero.create_new(
        name="Варг", faction_id="greenskins", archetype=archetype, max_hp=150.0
    )


class TestHeroDamageAndScarsInvariants:
    def test_hero_armor_can_fully_absorb_damage(self, sample_hero):
        artifact_armor = HeroArtifact(
            id="art_armor_01",
            name="Драконий панцирь",
            lore="...",
            slot=EquipmentSlot.ARMOR,
            category=ArmorCategory.CARAPACE,
            tier=4,
            stats=EquipmentStats(armor_bonus=30.0),
        )
        sample_hero.armor = artifact_armor

        # Урон меньше брони полностью поглощается героем (в отличие от Squad, нет мин. урона 1)
        is_lethal = sample_hero.take_damage(raw_damage=25.0)

        assert is_lethal is False
        assert sample_hero.state.current_hp == 150.0

    def test_hero_lethal_damage_and_scar_recovery(self, sample_hero):
        is_lethal = sample_hero.take_damage(raw_damage=500.0)

        assert is_lethal is True
        assert sample_hero.state.current_hp == 0.0

        scar1 = Scar(
            name="Разорванное плечо",
            description="...",
            modifier=MechanicalModifier(stat_name="damage", value=-2.0),
        )
        sample_hero.apply_scar(scar1, recovery_ticks=2)

        assert sample_hero.state.is_heavily_wounded is True
        assert sample_hero.state.is_alive is True
        assert sample_hero.state.wounded_ticks_remaining == 2
        assert sample_hero.state.current_hp == 1.0
        assert len(sample_hero.state.scars) == 1

        # Повторное ранение и наложение второго шрама
        scar2 = Scar(
            name="Выбитый глаз",
            description="...",
            modifier=MechanicalModifier(stat_name="initiative", value=-3.0),
        )
        sample_hero.apply_scar(scar2, recovery_ticks=4)

        assert sample_hero.state.wounded_ticks_remaining == 4
        assert len(sample_hero.state.scars) == 2

    def test_hero_modifiers_aggregation(self, sample_hero):
        perk = Perk(
            id="perk_berserk",
            name="Берсерк",
            description="...",
            level_required=1,
            modifier=MechanicalModifier(stat_name="damage", value=10.0),
            text_fragment="...",
        )
        scar = Scar(
            name="Хромота",
            description="...",
            modifier=MechanicalModifier(stat_name="speed", value=-0.5),
        )
        sample_hero.learn_perk(perk)
        sample_hero.apply_scar(scar, recovery_ticks=1)

        # Модификаторы: перк (10) + шрам (-0.5) + архетип триггер (5.0)
        modifiers = sample_hero.get_active_modifiers()
        stat_values = {m.stat_name: m.value for m in modifiers}

        assert len(modifiers) == 3
        assert stat_values["speed"] == -0.5
        assert stat_values["damage"] in (10.0, 5.0)

    def test_learn_perk_level_invariants(self, sample_hero):
        perk_high_level = Perk(
            id="perk_warlord",
            name="Полководец",
            description="...",
            level_required=10,
            modifier=MechanicalModifier(stat_name="morale", value=15.0),
            text_fragment="...",
        )

        with pytest.raises(HeroLevelTooLowError) as exc_info:
            sample_hero.learn_perk(perk_high_level)

        assert exc_info.value.current_level == 1
        assert exc_info.value.required_level == 10
        assert exc_info.value.perk_id == "perk_warlord"


class TestCommanderInvariants:
    def test_commander_experience_and_bounds(self):
        commander = Commander(
            name="Ольгерд",
            faction_id="baronial_troops",
            generation_type=CommanderGenerationType.PROCEDURAL,
            archetype=CommanderArchetype(
                id="arch_defender",
                name="Защитник",
                description="...",
                stats=CommanderArchetypeStats(ambush_resistance_modifier=0.3),
            ),
            trait=CommanderTrait(id="trait_stoic", name="Стойкий", text_fragment="..."),
        )

        commander.gain_experience(0)
        assert commander.state.experience == 0

        commander.gain_experience(150)
        assert commander.state.experience == 150

        with pytest.raises(NegativeExperienceError):
            commander.gain_experience(-50)

    def test_commander_characteristics_bounds(self):
        with pytest.raises(ValidationError):
            CommanderCharacteristics(authority=-5)

        with pytest.raises(ValidationError):
            CommanderCharacteristics(tactical_acumen=150)
