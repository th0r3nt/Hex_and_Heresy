"""
Сборщик статических промптов из markdown-файлов.
Реализация PromptBuilderProtocol: разрешает логические ключи каталога в файлы
на диске, лениво читает их и кэширует. Также дает доступ к PromptDiscovery.
"""

from pathlib import Path
from typing import Optional

from src.back.l03_infrastructure.llm.prompt.catalog import PromptDiscovery, resolve_prompt_key
from src.back.utils.logger import main_logger


class PromptBuilder:
    """
    Отвечает за чтение и склейку системных промптов из отдельных файлов (ролей, лора, черт).
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        discovery: Optional[PromptDiscovery] = None,
    ) -> None:
        self._base_dir = base_dir or Path(__file__).parent
        self._discovery = discovery or PromptDiscovery(base_dir=self._base_dir)
        self._cache: dict[str, str] = {}

    @property
    def discovery(self) -> PromptDiscovery:
        """Инструмент динамического обнаружения файлов промптов."""
        return self._discovery

    def build(self, keys: list[str]) -> str:
        """
        Принимает список логических ключей каталога (или готовых путей от
        discovery) и склеивает их содержимое в единый текст с двойным
        переносом строки.
        """
        blocks: list[str] = []

        for key in keys:
            content = self._load_file(resolve_prompt_key(key))
            if content:
                blocks.append(content)

        return "\n\n".join(blocks)

    def clear_cache(self) -> None:
        """Очищает кэш прочитанных файлов."""
        self._cache.clear()

    def _load_file(self, relative_path: str) -> str:
        """
        Лениво читает файл с диска или отдает его из кэша.
        """
        normalized_path = Path(relative_path).as_posix()

        if normalized_path in self._cache:
            return self._cache[normalized_path]

        file_path = self._base_dir / relative_path

        if not file_path.exists() or not file_path.is_file():
            main_logger.error(f"[PromptBuilder] Файл промпта не найден: {file_path}")
            return ""

        try:
            content = file_path.read_text(encoding="utf-8").strip()
            self._cache[normalized_path] = content
            return content
        except OSError as error:
            main_logger.error(f"[PromptBuilder] Ошибка при чтении файла {file_path}: {error}")
            return ""
