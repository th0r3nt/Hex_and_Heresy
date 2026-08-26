"""
Тесты сборщика промптов (LLM): разрешение логических ключей в файлы,
склейка, кэш и поведение при пропаже файла.
"""

from src.back.l01_domain.llm.prompts import PromptCatalog
from src.back.l01_domain.protocols.llm import PromptBuilderProtocol
from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder


class TestDomainContract:
    def test_builder_satisfies_prompt_builder_protocol(self):
        """Сервисы видят сборщик только через протокол домена."""
        assert isinstance(PromptBuilder(), PromptBuilderProtocol)


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

    def test_logical_key_is_resolved_to_a_nested_file(self, tmp_path):
        """Сервисы приносят ключи каталога, а не пути: 'base.persona' -> base/persona.md."""
        (tmp_path / "base").mkdir()
        (tmp_path / "base" / "persona.md").write_text("Ты - хронист.", encoding="utf-8")

        builder = PromptBuilder(base_dir=tmp_path)

        assert builder.build([PromptCatalog.BASE.PERSONA]) == "Ты - хронист."
