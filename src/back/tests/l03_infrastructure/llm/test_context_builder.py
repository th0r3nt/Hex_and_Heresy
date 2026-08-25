"""
Тесты сборщика изменчивого контекста: набор блоков под каждую роль
и их склейка в текст промпта.
"""

import pytest

from src.back.l01_domain.army.models.card.squad import Squad
from src.back.l01_domain.army.models.card.unit import BaseUnitStats, UnitArchetype
from src.back.l01_domain.army.models.characters.commanders import (
    Commander,
    CommanderArchetype,
    CommanderGenerationType,
    CommanderTrait,
)
from src.back.l01_domain.army.models.characters.heroes import Hero, HeroArchetype, HeroState
from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.common import CharacterGenerationType, FactionRace
from src.back.l01_domain.factions.constants import DiplomaticStance
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.diplomacy.messengers import Ambassador
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord, LordArchetype, LordTrait
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.battle_log import BattleDossier
from src.back.l01_domain.world.models.battleground import BattlefieldLootSite
from src.back.l01_domain.world.models.state import WorldState
from src.back.l03_infrastructure.llm.context.builder import ContextBuilder


def titles(blocks: list[ContextBlock]) -> list[str]:
    return [block.title for block in blocks]


def body(blocks: list[ContextBlock], title: str) -> str:
    return next(block.body for block in blocks if block.title == title)


def make_faction(faction_id: str, race: FactionRace, name: str) -> Faction:
    return Faction(
        id=faction_id,
        race=race,
        name=name,
        is_player_controlled=faction_id == "humans",
        lord=Lord(
            faction_id=faction_id,
            name=f"Лорд {name}",
            title="Лорд-командующий",
            archetype=LordArchetype(id="arch_lord", name="Бюрократ", description="..."),
            trait=LordTrait(id="trait_lord", name="Расчетливый", text_fragment="..."),
        ),
        headquarters=Headquarters(faction_id=faction_id, name="Цитадель"),
    )


@pytest.fixture
def builder() -> ContextBuilder:
    return ContextBuilder()


@pytest.fixture
def faction() -> Faction:
    return make_faction("humans", FactionRace.HUMANS, "Священная Империя")


@pytest.fixture
def counterpart() -> Faction:
    return make_faction("greenskins", FactionRace.GREENSKINS, "Орда Ржавых Клыков")


@pytest.fixture
def world_state(faction: Faction, counterpart: Faction) -> WorldState:
    state = WorldState()
    state.add_faction(faction)
    state.add_faction(counterpart)
    state.add_army(
        StrategicArmy(faction_id="humans", current_hex=HexCoordinates(q=0, r=0, s=0))
    )
    return state


@pytest.fixture
def army(world_state: WorldState) -> StrategicArmy:
    return next(iter(world_state.armies.values()))


@pytest.fixture
def ambassador() -> Ambassador:
    return Ambassador(
        faction_id="humans",
        name="Северин",
        traits=["Красноречивый"],
        target_faction_id="greenskins",
        directive="Выторговать мир до зимы.",
    )


@pytest.fixture
def commander() -> Commander:
    return Commander(
        name="Валленштейн",
        faction_id="humans",
        generation_type=CommanderGenerationType.PROCEDURAL,
        archetype=CommanderArchetype(id="arch", name="Осторожный", description="..."),
        trait=CommanderTrait(id="trait", name="Педант", text_fragment="..."),
    )


@pytest.fixture
def squad() -> Squad:
    archetype = UnitArchetype(
        id="unit_humans_sword",
        race=FactionRace.HUMANS,
        name="Мечники",
        tier=1,
        default_unit_count=100,
        base_stats=BaseUnitStats(max_hp=20.0),
    )
    return Squad.create_new(archetype=archetype)


class TestLord:
    def test_lord_sees_himself_faction_and_relations(
        self, builder: ContextBuilder, world_state: WorldState, faction: Faction, counterpart: Faction
    ):
        blocks = builder.build_lord_context(world_state, faction, counterpart)

        assert titles(blocks) == [
            "Твой личный статус",
            "Экономика фракции",
            "Дипломатическая обстановка",
        ]
        assert "Цитадель" in body(blocks, "Твой личный статус")

    def test_ambassador_before_the_throne_is_mentioned(
        self,
        builder: ContextBuilder,
        world_state: WorldState,
        faction: Faction,
        counterpart: Faction,
        ambassador: Ambassador,
    ):
        blocks = builder.build_lord_context(world_state, faction, counterpart, ambassador)

        assert "Обстановка в тронном зале" in titles(blocks)
        assert "Северин" in body(blocks, "Обстановка в тронном зале")

    def test_without_counterpart_lord_gets_a_war_overview(
        self, builder: ContextBuilder, world_state: WorldState, faction: Faction
    ):
        """
        Ответ на депешу собирается без второй фракции: вместо сводки по паре
        лорд получает общий список войн.
        """
        blocks = builder.build_lord_context(world_state, faction)

        assert "Внешние угрозы" in titles(blocks)
        assert "живет в мире" in body(blocks, "Внешние угрозы")

    def test_war_is_named_in_the_overview(
        self, builder: ContextBuilder, world_state: WorldState, faction: Faction
    ):
        relation = world_state.get_or_create_relation("humans", "greenskins")
        relation.stance = DiplomaticStance.WAR

        blocks = builder.build_lord_context(world_state, faction)

        assert "Орда Ржавых Клыков" in body(blocks, "Внешние угрозы")


class TestOtherRoles:
    def test_ambassador_knows_whose_citadel_he_stands_in(
        self,
        builder: ContextBuilder,
        world_state: WorldState,
        faction: Faction,
        counterpart: Faction,
        ambassador: Ambassador,
    ):
        blocks = builder.build_ambassador_context(
            world_state, ambassador, faction, counterpart
        )

        assert titles(blocks) == ["Твое положение", "Дипломатическая обстановка"]
        assert "Орда Ржавых Клыков" in body(blocks, "Твое положение")

    def test_commander_gets_his_army_and_the_world(
        self,
        builder: ContextBuilder,
        world_state: WorldState,
        commander: Commander,
        army: StrategicArmy,
    ):
        blocks = builder.build_commander_context(world_state, commander, army)

        assert titles(blocks) == ["Твое положение", "Состояние армии", "Обстановка в мире"]

    def test_hero_gets_tactical_block_only_in_battle(
        self, builder: ContextBuilder, world_state: WorldState
    ):
        hero = Hero(
            name="Зигфрид",
            faction_id="humans",
            archetype=HeroArchetype(
                id="arch_hero", name="Витязь", description="...", special_rule="..."
            ),
            max_hp=100.0,
            state=HeroState(current_hp=80.0),
        )

        assert titles(builder.build_hero_context(world_state, hero)) == ["Твое положение"]
        assert titles(
            builder.build_hero_context(world_state, hero, TacticalBattleState())
        ) == ["Твое положение", "Тактическая обстановка"]

    def test_nameless_squad_has_no_veteran_legend(
        self, builder: ContextBuilder, world_state: WorldState, squad: Squad
    ):
        blocks = builder.build_veteran_context(world_state, squad)

        assert "None" not in body(blocks, "Твое положение")
        assert "Мечники" in body(blocks, "Твое положение")

    def test_named_squad_tells_its_legend(
        self, builder: ContextBuilder, world_state: WorldState, squad: Squad
    ):
        squad.veterancy.promote(
            commander_name="Маркус",
            squad_nickname="Грязные стрелки",
            trait_name="Злопамятные",
            lore="Выжили под Черными топями.",
        )

        assert "Маркус" in body(builder.build_veteran_context(world_state, squad), "Твое положение")

    def test_gunsmith_sees_the_treasury(
        self, builder: ContextBuilder, world_state: WorldState, faction: Faction
    ):
        blocks = builder.build_gunsmith_context(world_state, faction)

        assert titles(blocks) == ["Твое положение", "Экономика фракции"]
        assert "не создал ни одного" in body(blocks, "Твое положение")

    def test_advisor_sees_the_macro_picture(
        self, builder: ContextBuilder, world_state: WorldState, faction: Faction
    ):
        blocks = builder.build_advisor_context(world_state, faction)

        assert titles(blocks) == [
            "Твое положение",
            "Обстановка в мире",
            "Экономика фракции",
            "Внешние угрозы",
        ]



class TestChronicler:
    def test_rumor_context_looks_at_the_whole_map(
        self, builder: ContextBuilder, world_state: WorldState, faction: Faction
    ):
        world_state.get_or_create_relation("humans", "greenskins").declare_war()

        blocks = builder.build_rumor_context(world_state, faction)

        assert titles(blocks) == [
            "Твое положение",
            "Обстановка в мире",
            "Войны на карте",
            "Экономика фракции",
        ]
        assert (
            "Священная Империя против Орда Ржавых Клыков" in body(blocks, "Войны на карте")
        )

    def test_rumor_context_without_faction_is_neutral(
        self, builder: ContextBuilder, world_state: WorldState
    ):
        """Бой без писаря: летописец рассказывает о мире, ничью сторону не держа."""
        blocks = builder.build_rumor_context(world_state)

        assert titles(blocks) == ["Обстановка в мире", "Войны на карте"]
        assert "Открытых войн" in body(blocks, "Войны на карте")

    def test_world_block_counts_rotting_battlefields(
        self, builder: ContextBuilder, world_state: WorldState
    ):
        world_state.add_battlefield_site(
            BattlefieldLootSite(
                origin_battle_id="b1",
                hex_coordinates=HexCoordinates(q=1, r=0, s=-1),
                residual_resonite=5.0,
            )
        )

        blocks = builder.build_rumor_context(world_state)

        assert "поля брани: 1" in body(blocks, "Обстановка в мире")

    def test_chronicle_context_marks_a_siege_massacre(
        self, builder: ContextBuilder, faction: Faction
    ):
        dossier = BattleDossier(battle_id="b1", started_tick=1, is_siege=True)

        text = body(builder.build_chronicle_context(dossier, faction), "Твое положение")

        assert "Священная Империя" in text
        assert "штурм цитадели" in text

    def test_ordinary_skirmish_adds_nothing(self, builder: ContextBuilder):
        dossier = BattleDossier(battle_id="b2", started_tick=1)

        assert builder.render(builder.build_chronicle_context(dossier)) == ""

class TestWarnings:
    def test_empty_treasury_is_flagged(self, builder: ContextBuilder, world_state: WorldState, faction: Faction):
        """Пустая казна и голод - триггеры внимания для модели."""
        blocks = builder.build_advisor_context(world_state, faction)

        assert "Казна пуста" in body(blocks, "Экономика фракции")

    def test_army_composition_is_reported(
        self,
        builder: ContextBuilder,
        world_state: WorldState,
        commander: Commander,
        army: StrategicArmy,
    ):
        blocks = builder.build_commander_context(world_state, commander, army)

        assert "0 отрядов" in body(blocks, "Состояние армии")


class TestRender:
    def test_filled_blocks_become_markdown_sections(self, builder: ContextBuilder):
        rendered = builder.render(
            [
                ContextBlock(title="Обстановка в мире", body="Ход 12, сумерки."),
                ContextBlock(title="Положение фракции", body="Казна пуста."),
            ]
        )

        assert rendered == (
            "## Обстановка в мире\nХод 12, сумерки.\n\n"
            "## Положение фракции\nКазна пуста."
        )

    def test_single_block_is_accepted(self, builder: ContextBuilder):
        assert builder.render(ContextBlock(title="Т", body="текст")) == "## Т\nтекст"

    def test_empty_blocks_are_dropped(self, builder: ContextBuilder):
        rendered = builder.render(
            [
                ContextBlock(title="Пустой"),
                ContextBlock(title="Обстановка боя", body="Фаза развертывания."),
                ContextBlock(title="Пробелы", body="   \n  "),
            ]
        )

        assert rendered == "## Обстановка боя\nФаза развертывания."

    def test_body_is_trimmed(self, builder: ContextBuilder):
        rendered = builder.render([ContextBlock(title="Т", body="\n  текст  \n\n")])

        assert rendered == "## Т\nтекст"

    def test_block_order_is_preserved(self, builder: ContextBuilder):
        rendered = builder.render(
            [
                ContextBlock(title="Первый", body="1"),
                ContextBlock(title="Второй", body="2"),
                ContextBlock(title="Третий", body="3"),
            ]
        )

        assert rendered.index("Первый") < rendered.index("Второй") < rendered.index("Третий")

    def test_nothing_to_say_renders_as_empty_string(self, builder: ContextBuilder):
        assert builder.render([]) == ""
        assert builder.render([ContextBlock(title="Пустой")]) == ""

    def test_role_context_renders_as_sections(
        self, builder: ContextBuilder, world_state: WorldState, faction: Faction, counterpart: Faction
    ):
        rendered = builder.render(builder.build_lord_context(world_state, faction, counterpart))

        assert rendered.startswith("## Твой личный статус\n")
        assert "\n\n## Экономика фракции\n" in rendered

    def test_custom_commander_biography_and_override_in_context(
        self, builder: ContextBuilder, world_state: WorldState, army: StrategicArmy
    ):
        commander = Commander(
            name="Ганс",
            faction_id="humans",
            generation_type=CharacterGenerationType.CUSTOM,
            archetype=CommanderArchetype(id="arch", name="Осторожный", description="..."),
            trait=CommanderTrait(id="trait", name="Педант", text_fragment="..."),
            custom_biography="Выжил в резне с гоблинами.",
            personality_prompt_override="Ненавидит зеленокожих и пьет дешевый ром.",
        )

        blocks = builder.build_commander_context(world_state, commander, army)
        rendered = builder.render(blocks)

        assert "Выжил в резне с гоблинами." in rendered
        assert "Ненавидит зеленокожих и пьет дешевый ром." in rendered

    def test_custom_hero_biography_and_override_in_context(
        self, builder: ContextBuilder, world_state: WorldState
    ):
        hero = Hero(
            name="Варг",
            faction_id="greenskins",
            archetype=HeroArchetype(
                id="arch_warrior", name="Воин", description="...", special_rule="..."
            ),
            max_hp=100.0,
            state=HeroState(current_hp=100.0),
            custom_biography="Бывший гладиатор арены.",
            personality_prompt_override="Всегда ищет драки один на один.",
        )

        blocks = builder.build_hero_context(world_state, hero)
        rendered = builder.render(blocks)

        assert "Бывший гладиатор арены." in rendered
        assert "Всегда ищет драки один на один." in rendered

    def test_custom_lord_biography_and_override_in_context(
        self, builder: ContextBuilder, world_state: WorldState, faction: Faction
    ):
        faction.lord.custom_biography = "Захватил трон в результате переворота."
        faction.lord.personality_prompt_override = "Крайне подозрителен ко всем послам."

        blocks = builder.build_lord_context(world_state, faction)
        rendered = builder.render(blocks)

        assert "Захватил трон в результате переворота." in rendered
        assert "Крайне подозрителен ко всем послам." in rendered