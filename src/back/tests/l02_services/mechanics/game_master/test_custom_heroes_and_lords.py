"""
Тесты генерации кастомных героев, лордов и советников.
"""

import pytest

from src.back.l01_domain.common import CharacterGenerationType, FactionRace, StatName
from src.back.l02_services.mechanics.game_master.custom.advisers import (
    CustomAdvisorDraftResponse,
    CustomAdvisorFactory,
)
from src.back.l02_services.mechanics.game_master.custom.heroes import (
    CustomHeroDraftResponse,
    CustomHeroFactory,
)
from src.back.l02_services.mechanics.game_master.custom.lords import (
    CustomLordDraftResponse,
    CustomLordFactory,
)
from src.back.tests.l02_services.mechanics.game_master.test_custom_commanders import (
    FakeLLMClient,
    FakePromptBuilder,
)


class TestCustomHeroesLordsAndAdvisors:
    @pytest.mark.asyncio
    async def test_successful_hero_generation(self):
        draft = CustomHeroDraftResponse(
            is_lore_friendly=True,
            name="Илай",
            archetype_name="Видящий смерть",
            archetype_description="Бывший полевой хирург.",
            special_rule="Видит линии смерти врагов.",
            max_hp=160.0,
            distilled_personality="Говорит тихо и меланхолично.",
            selected_trait_ids=["desiccation", "pragmatist"],
        )
        llm = FakeLLMClient(draft_response=draft)
        factory = CustomHeroFactory(llm_client=llm, prompt_builder=FakePromptBuilder())

        hero, message = await factory.create_hero(
            faction_id="congregation_of_the_meteorite",
            race=FactionRace.CONGREGATION_OF_THE_METEORITE,
            biography_text="Хирург, пораженный резонитом.",
        )

        assert hero is not None
        assert hero.name == "Илай"
        assert hero.max_hp == 160.0
        assert hero.special_rule == "Видит линии смерти врагов."
        assert len(hero.traits) == 2
        assert hero.generation_type == CharacterGenerationType.CUSTOM

        # Проверяем модификаторы от черты иссушения
        modifiers = hero.get_active_modifiers()
        stat_names = {m.stat_name for m in modifiers}
        assert StatName.HP_REGEN in stat_names
        assert "примкнуть к вашей армии" in message

    @pytest.mark.asyncio
    async def test_successful_lord_generation(self):
        draft = CustomLordDraftResponse(
            is_lore_friendly=True,
            name="Вальтер",
            title="Эрцгерцог",
            archetype_name="Владыка пошлин",
            archetype_description="Перекрыл ущелье стеной.",
            distilled_personality="Разговаривает языком налоговых счетов.",
            selected_trait_ids=["greedy", "bureaucrat"],
            tax_rate_bias=0.6,
            military_building_priority=0.2,
            diplomatic_aggression=0.3,
            bribery_susceptibility=0.8,
        )
        llm = FakeLLMClient(draft_response=draft)
        factory = CustomLordFactory(llm_client=llm, prompt_builder=FakePromptBuilder())

        lord, message = await factory.create_lord(
            faction_id="baronial_troops",
            race=FactionRace.BARONIAL_TROOPS,
            biography_text="Барон Медных врат.",
        )

        assert lord is not None
        assert lord.name == "Вальтер"
        assert lord.title == "Эрцгерцог"
        assert lord.display_name == "Эрцгерцог Вальтер"
        assert len(lord.traits) == 2
        trait_ids = [t.id for t in lord.traits]
        assert "trait_greedy" in trait_ids
        assert "trait_bureaucrat" in trait_ids
        assert "принимает правление" in message

    @pytest.mark.asyncio
    async def test_successful_advisor_generation(self):
        draft = CustomAdvisorDraftResponse(
            is_lore_friendly=True,
            name="Готфрид",
            title="Сенешаль",
            distilled_personality="Сухой бухгалтерский тон.",
            selected_trait_ids=["bureaucrat"],
        )
        llm = FakeLLMClient(draft_response=draft)
        factory = CustomAdvisorFactory(llm_client=llm, prompt_builder=FakePromptBuilder())

        advisor, message = await factory.create_advisor(
            faction_id="humans",
            race=FactionRace.HUMANS,
            biography_text="Управляющий расходами замка.",
        )

        assert advisor is not None
        assert advisor.name == "Готфрид"
        assert advisor.title == "Сенешаль"
        assert len(advisor.traits) == 1
        assert "Сенешаль Готфрид" in message
