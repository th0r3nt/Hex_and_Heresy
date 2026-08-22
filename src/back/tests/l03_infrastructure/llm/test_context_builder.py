"""
Тесты сборщика изменчивого контекста. Сами блоки пока заглушки, проверяется сборка.
"""

from src.back.l03_infrastructure.llm.context.builder import ContextBlock, ContextBuilder
from src.back.l01_domain.world.models.state import WorldState


class TestContextBlock:
    def test_blank_body_marks_block_empty(self):
        assert ContextBlock(title="Обстановка", body="   ").is_empty is True
        assert ContextBlock(title="Обстановка", body="Идет дождь").is_empty is False


class TestRendering:
    def test_empty_blocks_do_not_reach_the_prompt(self):
        builder = ContextBuilder()

        rendered = builder.render(
            [
                ContextBlock(title="Обстановка в мире", body="Ход 12, неоновые часы."),
                ContextBlock(title="Состояние армии"),
            ]
        )

        assert rendered == "## Обстановка в мире\nХод 12, неоновые часы."

    def test_blocks_are_joined_in_order(self):
        builder = ContextBuilder()

        rendered = builder.render(
            [
                ContextBlock(title="Первый", body="раз"),
                ContextBlock(title="Второй", body="два"),
            ]
        )

        assert rendered == "## Первый\nраз\n\n## Второй\nдва"

    def test_stubs_produce_empty_blocks_for_now(self):
        """Пока механики не наполнены, блоки пустые и просто не попадают в промпт."""
        builder = ContextBuilder()

        block = builder.build_world_context(WorldState())

        assert block.is_empty is True
        assert builder.render([block]) == ""
