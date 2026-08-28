"""
Тесты для src/back/l01_domain/factions/models/legendary.py

Шаблон легендарной личности обязан отливать полноценный агрегат: тот же
Lord/Commander/Hero, что получается у мастера игры из биографии игрока,
но с готовым характером и ссылкой на файл личности.
"""

from src.back.l01_domain.army.models.characters.commanders import CommanderCharacteristics
from src.back.l01_domain.common import (
    CharacterGenerationType,
    FactionRace,
    MechanicalModifier,
    StatName,
)
from src.back.l01_domain.factions.models.legendary import (
    LegendaryCommanderTemplate,
    LegendaryHeroTemplate,
    LegendaryLordTemplate,
)
from src.back.l01_domain.factions.models.lord import LordStrategicBias


class TestLegendaryLordTemplate:
    def _make_template(self) -> LegendaryLordTemplate:
        return LegendaryLordTemplate(
            id="lord_test_chancellor",
            race=FactionRace.HUMANS,
            name="Бенедикт",
            title="Канцлер",
            archetype="Верховный канцлер",
            prompt_ref="unique_personalities.humans.lords.Benedict_Strauss",
            trait_ids=["bureaucrat", "greedy"],
            bias=LordStrategicBias(tax_rate_bias=0.8, bribery_susceptibility=0.6),
            lore_description="Правит из полутемных кабинетов.",
        )

    def test_build_produces_legendary_lord(self):
        lord = self._make_template().build(faction_id="faction-1")

        assert lord.faction_id == "faction-1"
        assert lord.display_name == "Канцлер Бенедикт"
        assert lord.is_legendary
        assert lord.generation_type == CharacterGenerationType.LEGENDARY
        assert lord.legendary_prompt_ref.endswith("Benedict_Strauss")
        assert lord.lore_description == "Правит из полутемных кабинетов."

    def test_build_carries_bias_and_traits(self):
        lord = self._make_template().build(faction_id="faction-1")

        assert lord.bias.tax_rate_bias == 0.8
        assert lord.bias.bribery_susceptibility == 0.6
        assert [t.id for t in lord.traits] == ["trait_bureaucrat", "trait_greedy"]

    def test_unknown_trait_key_is_skipped(self):
        """Опечатка в геймдате не должна валить создание партии."""
        template = LegendaryLordTemplate(
            id="lord_test_broken",
            race=FactionRace.HUMANS,
            name="Некто",
            prompt_ref="unique_personalities.humans.lords.Benedict_Strauss",
            trait_ids=["bureaucrat", "trait_which_does_not_exist"],
        )

        lord = template.build(faction_id="faction-1")

        assert [t.id for t in lord.traits] == ["trait_bureaucrat"]

    def test_faction_id_property_points_to_race_catalog(self):
        assert self._make_template().faction_id == FactionRace.HUMANS.value

    def test_same_template_serves_several_parties(self):
        """Шаблон неизменяем: из него можно отлить лордов разным фракциям."""
        template = self._make_template()

        first = template.build(faction_id="faction-1")
        second = template.build(faction_id="faction-2")

        assert first.id != second.id
        assert first.faction_id == "faction-1"
        assert second.faction_id == "faction-2"


class TestLegendaryCommanderTemplate:
    def test_build_produces_legendary_commander(self):
        template = LegendaryCommanderTemplate(
            id="cmd_test_sentinel",
            race=FactionRace.ELFS,
            name="Каэлин",
            role_title="Страж переправ",
            prompt_ref="unique_personalities.elfs.commanders.Kaelin",
            trait_ids=["monolith"],
            characteristics=CommanderCharacteristics(
                authority=65, tactical_acumen=55, resilience=95, cunning=20
            ),
            fixed_equipment_ids=["wpn_elf_crystal_glaive"],
        )

        commander = template.build(faction_id="faction-2")

        assert commander.faction_id == "faction-2"
        assert commander.role_title == "Страж переправ"
        assert commander.is_legendary
        assert commander.generation_type == CharacterGenerationType.LEGENDARY
        assert commander.characteristics.resilience == 95
        assert commander.fixed_equipment_ids == ["wpn_elf_crystal_glaive"]
        assert [t.id for t in commander.traits] == ["trait_monolith"]


class TestLegendaryHeroTemplate:
    def test_build_produces_legendary_hero_at_full_health(self):
        template = LegendaryHeroTemplate(
            id="hero_test_maimed",
            race=FactionRace.HUMANS,
            name="Сэр Бэйлен",
            prompt_ref="unique_personalities.humans.heroes.Sir_Baylen_the_Maimed",
            trait_ids=["fatalist", "gladiator"],
            max_hp=320.0,
            special_rule="Искупление кровью",
            trigger_modifier=MechanicalModifier(
                stat_name=StatName.ARMOR, value=10.0, is_percentage=False
            ),
            lore_description="Поклялся не снимать латы.",
        )

        hero = template.build(faction_id="faction-3")

        assert hero.faction_id == "faction-3"
        assert hero.max_hp == 320.0
        assert hero.state.current_hp == 320.0
        assert hero.state.is_alive
        assert hero.is_legendary
        assert hero.generation_type == CharacterGenerationType.LEGENDARY
        assert hero.special_rule == "Искупление кровью"
        assert hero.trigger_modifier.stat_name == StatName.ARMOR
        assert hero.lore_description == "Поклялся не снимать латы."
        assert [t.id for t in hero.traits] == ["trait_fatalist", "trait_gladiator"]
