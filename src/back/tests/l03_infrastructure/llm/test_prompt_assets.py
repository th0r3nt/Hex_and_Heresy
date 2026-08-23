"""
Тесты корпуса промптов.

Кода в prompt/ пока нет (builder.py — проектная документация), но markdown-блоки
уже уезжают в контекст модели, поэтому проверяется их целостность: кодировка,
непустое содержимое и полнота уровней знаний low -> medium -> high -> max.
"""

from pathlib import Path
from typing import List

import pytest

from src.back.l03_infrastructure.llm import prompt as prompt_package

PROMPT_DIR = Path(prompt_package.__file__).parent
LORE_DIR = PROMPT_DIR / "lore"
PERSONALITIES_DIR = PROMPT_DIR / "unique_personalities"

KNOWLEDGE_LEVELS = {"low.md", "medium.md", "high.md", "max.md"}


def all_markdown() -> List[Path]:
    return sorted(PROMPT_DIR.rglob("*.md"))


def content_markdown() -> List[Path]:
    """Блоки лора и механик; личные досье персонажей пока заготовки."""
    return [path for path in all_markdown() if PERSONALITIES_DIR not in path.parents]


def faction_lore_directories() -> List[Path]:
    return sorted(
        p
        for p in (LORE_DIR / "factions").iterdir()
        if p.is_dir() and not p.name.startswith("__")
    )


def level_directories() -> List[Path]:
    return [LORE_DIR / "basic", LORE_DIR / "magic", *faction_lore_directories()]


class TestCorpusIntegrity:
    def test_corpus_is_not_lost(self):
        assert len(content_markdown()) > 50

    @pytest.mark.parametrize("path", all_markdown(), ids=lambda p: p.name)
    def test_markdown_is_valid_utf8(self, path: Path):
        path.read_text(encoding="utf-8")  # UnicodeDecodeError = битая кодировка

    @pytest.mark.parametrize(
        "path", content_markdown(), ids=lambda p: f"{p.parent.name}/{p.name}"
    )
    def test_content_block_is_filled(self, path: Path):
        assert path.read_text(encoding="utf-8").strip(), "Пустой блок съест токены впустую"


class TestKnowledgeLevels:
    @pytest.mark.parametrize("directory", level_directories(), ids=lambda p: p.name)
    def test_all_levels_are_present(self, directory: Path):
        names = {p.name for p in directory.glob("*.md")}

        assert KNOWLEDGE_LEVELS <= names

    def test_every_faction_has_its_own_lore(self):
        assert len(faction_lore_directories()) >= 6


class TestBaseLayers:
    @pytest.mark.parametrize(
        "relative",
        [
            "base/persona.md",
            "base/mechanics/economy.md",
            "base/mechanics/strategic.md",
            "base/mechanics/tactical.md",
        ],
    )
    def test_base_layer_exists(self, relative: str):
        assert (PROMPT_DIR / relative).is_file()

    def test_faction_identity_files_exist(self):
        identities = {p.stem for p in (PROMPT_DIR / "factions").glob("*.md")}

        assert {"humans", "elfs", "greenskins", "mercenaries"} <= identities


class TestUniquePersonalities:
    def test_placeholders_are_reserved(self):
        """
        Досье именных персонажей заведены, но пока пустые: наполнение впереди.
        """
        placeholders = list(PERSONALITIES_DIR.rglob("*.md"))

        assert placeholders
        assert all(p.suffix == ".md" for p in placeholders)
