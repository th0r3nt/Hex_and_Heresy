"""
Разрешение логических ключей промптов в файлы на диске и динамическое
обнаружение markdown-файлов.

Сам каталог ключей живет в домене (l01_domain/llm/prompts.py): здесь только
знание о том, что за ключом стоит markdown-файл и где он лежит.
"""

from pathlib import Path
from typing import Optional

from src.back.l01_domain.common import FactionRace

PROMPT_FILE_SUFFIX = ".md"


# ====================================================
# Разрешение ключей
# ====================================================


def resolve_prompt_key(key: str) -> str:
    """
    Переводит логический ключ каталога в относительный путь к файлу:
    'roles.chronicler.rumors' -> 'roles/chronicler/rumors.md'.

    Готовые относительные пути (их отдает PromptDiscovery) проходят насквозь.
    """
    if key.endswith(PROMPT_FILE_SUFFIX):
        return key
    return key.replace(".", "/") + PROMPT_FILE_SUFFIX


# ====================================================
# Динамическое обнаружение файлов
# ====================================================


class PromptDiscovery:
    """
    Инструмент динамического обнаружения файлов промптов на диске.
    Обеспечивает сбор коллекций трейтов, личностей и лора для мастера игры.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir or Path(__file__).parent

    def get_traits(self, category: Optional[str] = None) -> list[str]:
        """
        Возвращает относительные пути ко всем markdown-файлам черт характера.
        Если указана категория (например, 'psychological', 'unique/backgrounds',
        'unique/cursed_genes'), поиск ограничивается ею.
        """

        target_dir = self._base_dir / "traits"
        if category:
            target_dir = target_dir / category

        return self._collect_relative_md_files(target_dir)

    def get_unique_personalities(
        self,
        race: Optional[FactionRace] = None,
        role: Optional[str] = None,
    ) -> list[str]:
        """
        Возвращает относительные пути к файлам уникальных личностей.
        Поддерживает фильтрацию по расе и роли (commanders, heroes, lords).
        """

        target_dir = self._base_dir / "unique_personalities"
        if race:
            target_dir = target_dir / race.value
        if role:
            target_dir = target_dir / role

        return self._collect_relative_md_files(target_dir)

    def get_all_md_files(self, sub_dir: str = "") -> list[str]:
        """
        Рекурсивно возвращает относительные пути ко всем markdown-файлам
        в заданной поддиректории.
        """

        target_dir = self._base_dir / sub_dir if sub_dir else self._base_dir
        return self._collect_relative_md_files(target_dir)

    def _collect_relative_md_files(self, directory: Path) -> list[str]:
        if not directory.exists() or not directory.is_dir():
            return []

        results: list[str] = []
        for file_path in sorted(directory.rglob("*.md")):
            if file_path.is_file():
                rel_path = file_path.relative_to(self._base_dir).as_posix()
                results.append(rel_path)
        return results
