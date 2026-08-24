"""
Тесты статического реестра и сборщика промптов (LLM).
"""

from src.back.l01_domain.common import FactionRace
from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder
from src.back.l03_infrastructure.llm.prompt.catalog import (
    PromptCatalog,
    get_faction_prompt_path,
)


class TestPromptCatalog:
    def test_get_faction_prompt_path_maps_all_races(self):
        assert get_faction_prompt_path(FactionRace.HUMANS) == PromptCatalog.FACTIONS.HUMANS
        assert get_faction_prompt_path(FactionRace.ELFS) == PromptCatalog.FACTIONS.ELFS
        assert (
            get_faction_prompt_path(FactionRace.GREENSKINS)
            == PromptCatalog.FACTIONS.GREENSKINS
        )
        assert (
            get_faction_prompt_path(FactionRace.BARONIAL_TROOPS)
            == PromptCatalog.FACTIONS.BARONIAL_TROOPS
        )
        assert (
            get_faction_prompt_path(FactionRace.CONGREGATION_OF_THE_METEORITE)
            == PromptCatalog.FACTIONS.CONGREGATION_OF_THE_METEORITE
        )
        assert (
            get_faction_prompt_path(FactionRace.MERCENARIES)
            == PromptCatalog.FACTIONS.MERCENARIES
        )


class TestPromptBuilder:
    def test_build_concatenates_files_with_double_newlines(self, tmp_path):
        file_a = tmp_path / "a.md"
        file_b = tmp_path / "b.md"

        file_a.write_text("Текст А", encoding="utf-8")
        file_b.write_text("Текст Б", encoding="utf-8")

        builder = PromptBuilder(base_dir=tmp_path)
        result = builder.build(["a.md", "b.md"])

        assert result == "Текст А\n\nТекст Б"

    def test_build_strips_whitespace_from_files(self, tmp_path):
        file = tmp_path / "dirty.md"
        file.write_text("  Текст с пробелами \n \n", encoding="utf-8")

        builder = PromptBuilder(base_dir=tmp_path)
        result = builder.build(["dirty.md"])

        assert result == "Текст с пробелами"

    def test_caching_prevents_subsequent_file_reads(self, tmp_path):
        file = tmp_path / "cache_test.md"
        file.write_text("Оригинал", encoding="utf-8")

        builder = PromptBuilder(base_dir=tmp_path)

        # Первый вызов читает с диска и кэширует
        assert builder.build(["cache_test.md"]) == "Оригинал"

        # Меняем файл на диске
        file.write_text("Измененный текст", encoding="utf-8")

        # Второй вызов должен отдать кэшированную версию
        assert builder.build(["cache_test.md"]) == "Оригинал"

    def test_missing_file_is_ignored_and_logged(self, tmp_path, caplog):
        builder = PromptBuilder(base_dir=tmp_path)

        # Передаем несуществующий файл
        result = builder.build(["ghost.md"])

        assert result == ""
        assert "не найден" in caplog.text
        assert "ghost.md" in caplog.text

    def test_missing_file_does_not_break_valid_files(self, tmp_path):
        valid = tmp_path / "valid.md"
        valid.write_text("Существующий файл", encoding="utf-8")

        builder = PromptBuilder(base_dir=tmp_path)
        result = builder.build(["ghost.md", "valid.md"])

        assert result == "Существующий файл"
