"""
Тесты сборщика изменчивого контекста: набор блоков и их склейка в текст промпта.

Сами блоки пока заглушки (механики не готовы), поэтому проверяются контракт
методов и правила рендера, на которые опираются сервисы.
"""

import pytest

from src.back.l01_domain.army.models.strategic import StrategicArmy
from src.back.l01_domain.combat.models.state import TacticalBattleState
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.factions.models.buildings import Headquarters
from src.back.l01_domain.factions.models.faction import Faction
from src.back.l01_domain.factions.models.lord import Lord, LordArchetype, LordTrait
from src.back.l01_domain.llm.models.context import ContextBlock
from src.back.l01_domain.maps.models.strategic import HexCoordinates
from src.back.l01_domain.world.models.state import WorldState
from src.back.l03_infrastructure.llm.context.builder import ContextBuilder


@pytest.fixture
def builder() -> ContextBuilder:
    return ContextBuilder()


@pytest.fixture
def faction() -> Faction:
    return Faction(
        id="humans",
        race=FactionRace.HUMANS,
        name="Священная Империя",
        is_player_controlled=True,
        lord=Lord(
            faction_id="humans",
            name="Валленштейн",
            title="Лорд-командующий",
            archetype=LordArchetype(id="arch_lord", name="Бюрократ", description="..."),
            trait=LordTrait(id="trait_lord", name="Расчетливый", text_fragment="..."),
        ),
        headquarters=Headquarters(faction_id="humans", name="Цитадель"),
    )


@pytest.fixture
def world_state(faction: Faction) -> WorldState:
    state = WorldState()
    state.add_faction(faction)
    state.add_army(
        StrategicArmy(faction_id="humans", current_hex=HexCoordinates(q=0, r=0, s=0))
    )
    return state


class TestBlocks:
    def test_world_block_is_titled(self, builder: ContextBuilder, world_state: WorldState):
        block = builder.build_world_context(world_state)

        assert isinstance(block, ContextBlock)
        assert block.title == "Обстановка в мире"

    def test_faction_block_is_titled(self, builder: ContextBuilder, faction: Faction):
        assert builder.build_faction_context(faction).title == "Положение фракции"

    def test_army_block_is_titled(self, builder: ContextBuilder, world_state: WorldState):
        army = next(iter(world_state.armies.values()))

        assert builder.build_army_context(army).title == "Состояние армии"

    def test_diplomacy_block_is_titled(self, builder: ContextBuilder, world_state: WorldState):
        block = builder.build_diplomacy_context(world_state, faction_id="humans")

        assert block.title == "Дипломатическая обстановка"

    def test_diplomacy_block_accepts_a_counterpart(
        self, builder: ContextBuilder, world_state: WorldState
    ):
        block = builder.build_diplomacy_context(
            world_state, faction_id="humans", counterpart_id="greenskins"
        )

        assert block.title == "Дипломатическая обстановка"

    def test_battle_block_is_titled(self, builder: ContextBuilder):
        assert builder.build_battle_context(TacticalBattleState()).title == "Обстановка боя"

    def test_blocks_are_still_stubs(self, builder: ContextBuilder, world_state: WorldState):
        """
        Механики не наполнены, поэтому блоки пустые и в промпт не попадают.
        Тест падает, когда появится первое наполнение — это сигнал обновить рендер-тесты.
        """
        assert builder.build_world_context(world_state).is_empty


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

    def test_stub_blocks_render_to_nothing(
        self, builder: ContextBuilder, world_state: WorldState, faction: Faction
    ):
        blocks = [
            builder.build_world_context(world_state),
            builder.build_faction_context(faction),
            builder.build_battle_context(TacticalBattleState()),
        ]

        assert builder.render(blocks) == ""
