"""
Интеграционные тесты целостности каталога промптов против реальной файловой системы.
Гарантируют отсутствие рассинхронизации между константами кода и файлами .md на диске.
"""

from pathlib import Path

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l03_infrastructure.llm.prompt.builder import PromptBuilder
from src.back.l03_infrastructure.llm.prompt.catalog import (
    PromptCatalog,
    PromptDiscovery,
    get_chronicler_writing_path,
    get_faction_prompt_path,
)


def _collect_all_catalog_constants(cls: type) -> list[str]:
    """
    Рекурсивно извлекает все строковые константы из вложенных классов каталога.
    """
    constants: list[str] = []
    for attr_name in dir(cls):
        if attr_name.startswith("_"):
            continue
        attr_val = getattr(cls, attr_name)
        if isinstance(attr_val, str):
            constants.append(attr_val)
        elif isinstance(attr_val, type):
            constants.extend(_collect_all_catalog_constants(attr_val))
    return constants


@pytest.fixture
def prompt_base_dir() -> Path:
    """Путь к корневой директории промптов в инфраструктурном слое."""
    base_dir = Path(__file__).resolve().parents[3] / "l03_infrastructure" / "llm" / "prompt"
    assert base_dir.exists() and base_dir.is_dir()
    return base_dir


class TestPromptCatalogIntegrity:
    def test_all_catalog_constants_exist_on_disk(self, prompt_base_dir: Path):
        """
        Проверяет, что каждый путь, объявленный в PromptCatalog,
        указывает на реально существующий файл (а не директорию).
        """
        all_paths = _collect_all_catalog_constants(PromptCatalog)
        assert len(all_paths) > 0, "Каталог промптов не должен быть пустым"

        missing_or_invalid: list[str] = []
        for rel_path in all_paths:
            file_path = prompt_base_dir / rel_path
            if not file_path.exists():
                missing_or_invalid.append(f"Файл не существует: {rel_path}")
            elif not file_path.is_file():
                missing_or_invalid.append(
                    f"Путь указывает на директорию, а не файл: {rel_path}"
                )
            elif file_path.stat().st_size == 0:
                missing_or_invalid.append(f"Файл пуст: {rel_path}")

        assert (
            not missing_or_invalid
        ), "Обнаружены невалидные пути в PromptCatalog:\n" + "\n".join(missing_or_invalid)

    @pytest.mark.parametrize("race", list(FactionRace))
    def test_all_factions_have_valid_prompt_files(
        self, prompt_base_dir: Path, race: FactionRace
    ):
        """Проверяет маппинг описаний фракций для всех доступных рас."""
        rel_path = get_faction_prompt_path(race)
        file_path = prompt_base_dir / rel_path
        assert file_path.is_file(), f"Файл фракции для {race.value} не найден: {rel_path}"

    @pytest.mark.parametrize("race", [None, *list(FactionRace)])
    def test_all_chronicler_writing_styles_exist(
        self, prompt_base_dir: Path, race: FactionRace | None
    ):
        """Проверяет стили написания летописца для всех рас и нейтрального режима."""
        rel_path = get_chronicler_writing_path(race)
        file_path = prompt_base_dir / rel_path
        assert file_path.is_file(), f"Стиль летописца для {race} не найден: {rel_path}"


class TestPromptDiscovery:
    def test_discovery_finds_all_traits(self, prompt_base_dir: Path):
        discovery = PromptDiscovery(base_dir=prompt_base_dir)
        traits = discovery.get_traits()

        assert len(traits) >= 20, "Ожидалось не менее 20 файлов черт характера"
        for trait_path in traits:
            assert trait_path.startswith("traits/"), f"Некорректный путь трейта: {trait_path}"
            assert trait_path.endswith(".md")
            assert (prompt_base_dir / trait_path).is_file()

    def test_discovery_traits_by_category(self, prompt_base_dir: Path):
        discovery = PromptDiscovery(base_dir=prompt_base_dir)

        psychological = discovery.get_traits("psychological")
        assert len(psychological) >= 10
        assert all("psychological" in path for path in psychological)

        cursed_genes = discovery.get_traits("unique/cursed_genes")
        assert len(cursed_genes) == 8
        assert all("cursed_genes" in path for path in cursed_genes)

    def test_discovery_finds_unique_personalities(self, prompt_base_dir: Path):
        discovery = PromptDiscovery(base_dir=prompt_base_dir)
        personalities = discovery.get_unique_personalities()

        assert len(personalities) >= 20, "Ожидалось не менее 20 файлов уникальных личностей"
        for p_path in personalities:
            assert p_path.startswith("unique_personalities/")
            assert (prompt_base_dir / p_path).is_file()

    def test_discovery_personalities_filtered_by_race_and_role(self, prompt_base_dir: Path):
        discovery = PromptDiscovery(base_dir=prompt_base_dir)

        human_commanders = discovery.get_unique_personalities(
            race=FactionRace.HUMANS, role="commanders"
        )
        assert len(human_commanders) >= 3
        assert all("humans/commanders" in path for path in human_commanders)

    def test_prompt_builder_loads_discovered_files(self, prompt_base_dir: Path):
        builder = PromptBuilder(base_dir=prompt_base_dir)
        traits = builder.discovery.get_traits("unique/backgrounds")

        assert len(traits) >= 5
        content = builder.build(traits)
        assert "Аристократ" in content
        assert "Инквизитор" in content
