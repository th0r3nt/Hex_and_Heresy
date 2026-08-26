"""
Тесты инвариантов полководцев, героев, лордов, перков, шрамов и артефактов.
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
    CommanderCharacteristics,
)
from src.back.l01_domain.army.models.characters.heroes import (
    Hero,
    Perk,
    Scar,
)
from src.back.l01_domain.common import (
    CharacterGenerationType,
    MechanicalModifier,
    StatName,
)
from src.back.l01_domain.exceptions.army import HeroLevelTooLowError, NegativeExperienceError
from src.back.l01_domain.factions.models.lord import Lord


@pytest.fixture
def sample_hero() -> Hero:
    return Hero.create_new(
        name="Варг",
        faction_id="greenskins",
        special_rule="Ярость",
        trigger_modifier=MechanicalModifier(stat_name=StatName.DAMAGE, value=5.0),
        max_hp=150.0,
        generation_type=CharacterGenerationType.CUSTOM,
        custom_biography="Бывший раб гладиаторских ям.",
        personality_prompt_override="Крайне агрессивен в рукопашной.",
    )


class TestHeroCustomizationAndInvariants:
    def test_custom_hero_fields(self, sample_hero: Hero):
        assert sample_hero.generation_type == CharacterGenerationType.CUSTOM
        assert sample_hero.custom_biography == "Бывший раб гладиаторских ям."
        assert sample_hero.personality_prompt_override == "Крайне агрессивен в рукопашной."
        assert sample_hero.is_legendary is False

    def test_hero_armor_can_fully_absorb_damage(self, sample_hero: Hero):
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

        is_lethal = sample_hero.take_damage(raw_damage=25.0)

        assert is_lethal is False
        assert sample_hero.state.current_hp == 150.0

    def test_hero_lethal_damage_and_scar_recovery(self, sample_hero: Hero):
        is_lethal = sample_hero.take_damage(raw_damage=500.0)

        assert is_lethal is True
        assert sample_hero.state.current_hp == 0.0

        scar1 = Scar(
            name="Разорванное плечо",
            description="...",
            modifier=MechanicalModifier(stat_name=StatName.DAMAGE, value=-2.0),
        )
        sample_hero.apply_scar(scar1, recovery_ticks=2)

        assert sample_hero.state.is_heavily_wounded is True
        assert sample_hero.state.is_alive is True
        assert sample_hero.state.wounded_ticks_remaining == 2
        assert sample_hero.state.current_hp == 1.0
        assert len(sample_hero.state.scars) == 1

        scar2 = Scar(
            name="Выбитый глаз",
            description="...",
            modifier=MechanicalModifier(stat_name=StatName.INITIATIVE, value=-3.0),
        )
        sample_hero.apply_scar(scar2, recovery_ticks=4)

        assert sample_hero.state.wounded_ticks_remaining == 4
        assert len(sample_hero.state.scars) == 2

    def test_hero_modifiers_aggregation(self, sample_hero: Hero):
        perk = Perk(
            id="perk_berserk",
            name="Берсерк",
            description="...",
            level_required=1,
            modifier=MechanicalModifier(stat_name=StatName.DAMAGE, value=10.0),
            text_fragment="...",
        )
        scar = Scar(
            name="Хромота",
            description="...",
            modifier=MechanicalModifier(stat_name=StatName.SPEED, value=-0.5),
        )
        sample_hero.learn_perk(perk)
        sample_hero.apply_scar(scar, recovery_ticks=1)

        modifiers = sample_hero.get_active_modifiers()
        stat_values = {m.stat_name: m.value for m in modifiers}

        assert len(modifiers) == 3
        assert stat_values["speed"] == -0.5

    def test_learn_perk_level_invariants(self, sample_hero: Hero):
        perk_high_level = Perk(
            id="perk_warlord",
            name="Полководец",
            description="...",
            level_required=10,
            modifier=MechanicalModifier(stat_name=StatName.MORALE, value=15.0),
            text_fragment="...",
        )

        with pytest.raises(HeroLevelTooLowError) as exc_info:
            sample_hero.learn_perk(perk_high_level)

        assert exc_info.value.current_level == 1
        assert exc_info.value.required_level == 10
        assert exc_info.value.perk_id == "perk_warlord"


class TestLordAndCommanderCustomizationInvariants:
    def test_custom_lord_fields(self):
        lord = Lord(
            faction_id="humans",
            name="Бенедикт",
            title="Канцлер",
            generation_type=CharacterGenerationType.CUSTOM,
            custom_biography="Поднялся из счетоводов гильдии.",
            personality_prompt_override="Помешан на проверке налоговых деклараций.",
        )

        assert lord.generation_type == CharacterGenerationType.CUSTOM
        assert lord.custom_biography == "Поднялся из счетоводов гильдии."
        assert lord.personality_prompt_override == "Помешан на проверке налоговых деклараций."
        assert lord.display_name == "Канцлер Бенедикт"

    def test_commander_experience_and_bounds(self):
        commander = Commander(
            name="Ольгерд",
            faction_id="baronial_troops",
            role_title="Защитник",
            generation_type=CharacterGenerationType.PROCEDURAL,
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
