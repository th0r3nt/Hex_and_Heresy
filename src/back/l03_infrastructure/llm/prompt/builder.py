"""
Сборщик статических промптов из markdown-файлов.
Использует ленивую загрузку и кэширование, чтобы минимизировать дисковые операции.
"""

from pathlib import Path
from typing import Optional

from src.back.utils.logger import main_logger


class PromptBuilder:
    """
    Отвечает за сборку системного промпта из отдельных файлов (ролей, лора, черт).
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        # По умолчанию берем директорию, в которой лежит этот файл
        self._base_dir = base_dir or Path(__file__).parent
        self._cache: dict[str, str] = {}

    def build(self, keys: list[str]) -> str:
        """
        Принимает список относительных путей (констант из PromptCatalog)
        и склеивает их содержимое в единый текст с двойным переносом строки.
        """
        blocks: list[str] = []

        for key in keys:
            content = self._load_file(key)
            if content:
                blocks.append(content)

        # Склеиваем блоки, чтобы они были разделены пустой строкой
        return "\n\n".join(blocks)

    def _load_file(self, relative_path: str) -> str:
        """
        Лениво читает файл с диска или отдает его из кэша.
        """
        if relative_path in self._cache:
            return self._cache[relative_path]

        file_path = self._base_dir / relative_path

        if not file_path.exists() or not file_path.is_file():
            main_logger.error(f"[PromptBuilder] Файл промпта не найден: {file_path}")
            # Возвращаем пустую строку, чтобы не ронять всю игру из-за одного битого пути,
            # но оставляем след в логах для отладки
            return ""

        try:
            content = file_path.read_text(encoding="utf-8").strip()
            self._cache[relative_path] = content
            return content
        except OSError as error:
            main_logger.error(f"[PromptBuilder] Ошибка при чтении файла {file_path}: {error}")
            return ""
