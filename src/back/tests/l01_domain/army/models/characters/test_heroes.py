"""
Тесты для src/back/l01_domain/army/models/characters/heroes.py
"""

import pytest
from pydantic import ValidationError

from src.back.l01_domain.army.constants import EquipmentSlot
from src.back.l01_domain.army.models.card.equipment import EquipmentStats
from src.back.l01_domain.army.models.characters.artifacts import HeroArtifact
from src.back.l01_domain.common import MechanicalModifier
from src.back.l01_domain.army.models.characters.heroes import (
    Hero,
    HeroArchetype,
    Perk,
    Scar,
)

from src.back.l01_domain.exceptions import HeroLevelTooLowError


@pytest.fixture
def unkillable_archetype() -> HeroArchetype:
    return HeroArchetype(
        id="archetype_unkillable",
        name="Неубиваемый",
        description="Выжил после прямого попадания пушечного ядра.",
        special_rule="Второе дыхание: раз за бой не умирает от смертельного удара.",
    )


@pytest.fixture
def resilience_perk() -> Perk:
    return Perk(
        id="perk_iron_gut",
        name="Железное брюхо",
        description="Ещё немного брони на пустое место.",
        level_required=5,
        modifier=MechanicalModifier(stat_name="armor", value=2.0),
        text_fragment="Ты хвастаешься шрамом от ядра при каждой возможности.",
    )


@pytest.fixture
def limp_scar() -> Scar:
    return Scar(
        name="Хромота",
        description="-1 к скорости перемещения после тяжёлого ранения в ногу.",
        modifier=MechanicalModifier(stat_name="speed", value=-1.0),
    )


@pytest.fixture
def hero_armor() -> HeroArtifact:
    return HeroArtifact(
        id="armor_test_hero_plate",
        name="Тестовые латы героя",
        lore="Тяжёлая броня для проверки урона.",
        slot=EquipmentSlot.ARMOR,
        tier=3,
        stats=EquipmentStats(armor_bonus=10.0),
    )


class TestHeroArchetype:
    def test_trigger_modifier_is_optional(self, unkillable_archetype):
        assert unkillable_archetype.trigger_modifier is None

    def test_is_frozen(self, unkillable_archetype):
        with pytest.raises(ValidationError):
            unkillable_archetype.name = "Другое имя"


class TestPerk:
    def test_level_required_is_bounded_by_max_hero_level(self):
        with pytest.raises(ValidationError):
            Perk(
                id="perk_broken",
                name="Сломанный перк",
                description="...",
                level_required=21,
                modifier=MechanicalModifier(stat_name="damage", value=1.0),
                text_fragment="...",
            )


class TestHero:
    def test_create_new_starts_at_full_health(self, unkillable_archetype):
        hero = Hero.create_new(
            name="Гром", faction_id="greenskins", archetype=unkillable_archetype, max_hp=300.0
        )

        assert hero.state.current_hp == 300.0
        assert hero.state.is_alive is True
        assert hero.display_name == "Гром"

    def test_is_attached_reflects_squad_assignment(self, unkillable_archetype):
        hero = Hero.create_new(
            name="Гром", faction_id="greenskins", archetype=unkillable_archetype, max_hp=300.0
        )
        assert hero.is_attached is False

        hero.attach_to_squad("squad_ironsides")
        assert hero.is_attached is True

        hero.detach_from_squad()
        assert hero.is_attached is False

    def test_active_modifiers_combine_perks_and_scars(
        self, unkillable_archetype, resilience_perk, limp_scar
    ):
        # У архетипа нет trigger_modifier — он не должен ничего добавлять.
        hero = Hero.create_new(
            name="Гром", faction_id="greenskins", archetype=unkillable_archetype, max_hp=300.0
        )
        hero.chosen_perks.append(resilience_perk)
        hero.state.scars.append(limp_scar)

        modifiers = hero.get_active_modifiers()

        assert resilience_perk.modifier in modifiers
        assert limp_scar.modifier in modifiers
        assert len(modifiers) == 2

    def test_archetype_trigger_modifier_is_included_when_present(self):
        archetype = HeroArchetype(
            id="archetype_with_trigger",
            name="С триггером",
            description="...",
            special_rule="При падении ХП до 0 автоматически исцеляется на 10%.",
            trigger_modifier=MechanicalModifier(
                stat_name="hp_regen", value=0.1, is_percentage=True
            ),
        )
        hero = Hero.create_new(
            name="Тест", faction_id="humans", archetype=archetype, max_hp=100.0
        )

        modifiers = hero.get_active_modifiers()

        assert len(modifiers) == 1
        assert modifiers[0].stat_name == "hp_regen"

    def test_take_damage_ignores_armor_absorbed_hits(self, unkillable_archetype, hero_armor):
        hero = Hero.create_new(
            name="Гром", faction_id="greenskins", archetype=unkillable_archetype, max_hp=300.0
        )
        hero.armor = hero_armor  # armor_bonus == 10.0

        is_dead = hero.take_damage(raw_damage=5.0)

        # В отличие от Squad.take_damage, у героя нет гарантированного
        # минимального урона в 1 единицу — броня может погасить удар целиком.
        assert is_dead is False
        assert hero.state.current_hp == 300.0

    def test_take_damage_applies_net_damage_above_armor(
        self, unkillable_archetype, hero_armor
    ):
        hero = Hero.create_new(
            name="Гром", faction_id="greenskins", archetype=unkillable_archetype, max_hp=300.0
        )
        hero.armor = hero_armor  # armor_bonus == 10.0

        hero.take_damage(raw_damage=50.0)

        assert hero.state.current_hp == 260.0  # 300 - (50 - 10)

    def test_take_damage_returns_true_on_lethal_hit(self, unkillable_archetype):
        hero = Hero.create_new(
            name="Гром", faction_id="greenskins", archetype=unkillable_archetype, max_hp=50.0
        )

        is_dead = hero.take_damage(raw_damage=999.0)

        assert is_dead is True
        assert hero.state.current_hp == 0.0

    def test_apply_scar_marks_hero_as_heavily_wounded_instead_of_dead(
        self, unkillable_archetype, limp_scar
    ):
        hero = Hero.create_new(
            name="Гром", faction_id="greenskins", archetype=unkillable_archetype, max_hp=50.0
        )
        hero.take_damage(raw_damage=999.0)  # ХП упало до 0

        hero.apply_scar(limp_scar, recovery_ticks=3)

        assert hero.state.is_heavily_wounded is True
        assert hero.state.is_alive is True
        assert hero.state.wounded_ticks_remaining == 3
        assert hero.state.current_hp == 1.0  # герой не остаётся с 0 хп
        assert limp_scar in hero.state.scars

    def test_learn_perk_respects_level_requirement(
        self, unkillable_archetype, resilience_perk
    ):
        hero = Hero.create_new(
            name="Гром", faction_id="greenskins", archetype=unkillable_archetype, max_hp=300.0
        )
        hero.state.level = 5

        hero.learn_perk(resilience_perk)

        assert resilience_perk in hero.chosen_perks

    def test_learn_perk_rejects_perk_above_current_level(
        self, unkillable_archetype, resilience_perk
    ):
        hero = Hero.create_new(
            name="Гром", faction_id="greenskins", archetype=unkillable_archetype, max_hp=300.0
        )
        hero.state.level = 1  # перк требует 5-й уровень

        with pytest.raises(HeroLevelTooLowError):
            hero.learn_perk(resilience_perk)
