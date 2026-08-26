"""
Интеграционные тесты целостности каталога промптов и единого реестра черт.

Каталог логических ключей живет в домене, файлы - в инфраструктуре: здесь
проверяется, что каждый доменный ключ разрешается в реальный непустой файл.
"""

from pathlib import Path
import pytest

from src.back.l01_domain.army.models.characters.traits import (
    TRAITS_CATALOG,
    TraitCategory,
    list_traits,
)
from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.llm.prompts import (
    PromptCatalog,
    get_chronicler_writing_key,
    get_faction_prompt_key,
)
from src.back.l03_infrastructure.llm.prompt.catalog import (
    PromptDiscovery,
    resolve_prompt_key,
)


def _collect_all_catalog_constants(cls: type) -> list[str]:
    """Рекурсивно извлекает все строковые ключи из вложенных классов каталога."""
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


class TestPromptKeyResolution:
    def test_dotted_key_becomes_markdown_path(self):
        assert resolve_prompt_key("roles.chronicler.rumors") == "roles/chronicler/rumors.md"
        assert resolve_prompt_key("base.persona") == "base/persona.md"

    def test_ready_paths_from_discovery_pass_through(self):
        """PromptDiscovery отдает готовые относительные пути - их трогать нельзя."""
        rel_path = "unique_personalities/humans/commanders/hoffmann.md"
        assert resolve_prompt_key(rel_path) == rel_path


class TestPromptCatalogIntegrity:
    def test_all_catalog_keys_exist_on_disk(self, prompt_base_dir: Path):
        """Проверяет, что каждый ключ PromptCatalog разрешается в реальный файл."""
        all_keys = _collect_all_catalog_constants(PromptCatalog)
        assert len(all_keys) > 0, "Каталог промптов не должен быть пустым"

        missing_or_invalid: list[str] = []
        for key in all_keys:
            rel_path = resolve_prompt_key(key)
            file_path = prompt_base_dir / rel_path

            if not file_path.exists():
                missing_or_invalid.append(f"Файл не существует: {key} -> {rel_path}")
            elif not file_path.is_file():
                missing_or_invalid.append(
                    f"Ключ указывает на директорию, а не файл: {key} -> {rel_path}"
                )
            elif file_path.stat().st_size == 0:
                missing_or_invalid.append(f"Файл пуст: {key} -> {rel_path}")

        assert (
            not missing_or_invalid
        ), "Обнаружены невалидные ключи в PromptCatalog:\n" + "\n".join(missing_or_invalid)

    def test_catalog_keys_carry_no_file_paths(self):
        """
        Домен не должен знать о markdown-файлах: ни расширений, ни слешей
        в ключах быть не может.
        """
        for key in _collect_all_catalog_constants(PromptCatalog):
            assert "/" not in key, f"Ключ каталога похож на путь: {key}"
            assert not key.endswith(".md"), f"Ключ каталога несет расширение файла: {key}"

    @pytest.mark.parametrize("race", list(FactionRace))
    def test_all_factions_have_valid_prompt_files(
        self, prompt_base_dir: Path, race: FactionRace
    ):
        """Проверяет маппинг описаний фракций для всех доступных рас."""
        rel_path = resolve_prompt_key(get_faction_prompt_key(race))
        file_path = prompt_base_dir / rel_path
        assert file_path.is_file(), f"Файл фракции для {race.value} не найден: {rel_path}"

    @pytest.mark.parametrize("race", [None, *list(FactionRace)])
    def test_all_chronicler_writing_styles_exist(
        self, prompt_base_dir: Path, race: FactionRace | None
    ):
        """Проверяет стили написания летописца для всех рас и нейтрального режима."""
        rel_path = resolve_prompt_key(get_chronicler_writing_key(race))
        file_path = prompt_base_dir / rel_path
        assert file_path.is_file(), f"Стиль летописца для {race} не найден: {rel_path}"


class TestTraitsCatalogIntegrity:
    def test_traits_catalog_contains_all_twenty_four_traits(self):
        """Проверяет, что реестр содержит ровно 24 сбалансированные черты."""
        assert len(TRAITS_CATALOG) == 24

        for trait_id, trait in TRAITS_CATALOG.items():
            assert trait.id.startswith("trait_")
            assert len(trait.name) > 0
            assert len(trait.prompt_text) >= 20, f"Промпт черты {trait_id} слишком короткий"
            assert "### Черта:" in trait.format_prompt()

    def test_traits_catalog_categories(self):
        """Проверяет разбиение черт по категориям."""
        psychological = list_traits(TraitCategory.PSYCHOLOGICAL)
        assert len(psychological) == 11

        backgrounds = list_traits(TraitCategory.BACKGROUND)
        assert len(backgrounds) == 5

        cursed_genes = list_traits(TraitCategory.CURSED_GENE)
        assert len(cursed_genes) == 8


class TestPromptDiscovery:
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
