"""
Проверка границ слоев бэкэнда (docs/RULES.md) разбором AST.

Правила простые: домен не знает ни о ком, сервисы знают только домен.
Тест ловит нарушение сразу, а не через полгода, когда фасад уже никак
не отвязать от файловой системы.
"""

import ast
from pathlib import Path

import pytest

BACK_DIR = Path(__file__).resolve().parents[1]

DOMAIN = "src.back.l01_domain"
SERVICES = "src.back.l02_services"
INFRASTRUCTURE = "src.back.l03_infrastructure"
API = "src.back.l04_api"

# Слой -> пакеты, импортировать которые ему запрещено
FORBIDDEN_IMPORTS = {
    "l01_domain": (SERVICES, INFRASTRUCTURE, API),
    "l02_services": (INFRASTRUCTURE, API),
}


def _iter_imported_modules(source: str) -> list[str]:
    """Полные имена модулей из всех import и from-import файла."""
    tree = ast.parse(source)
    modules: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            # Относительные импорты слой не пересекают
            if node.level == 0 and node.module:
                modules.append(node.module)

    return modules


def _python_files(layer: str) -> list[Path]:
    return sorted(
        path
        for path in (BACK_DIR / layer).rglob("*.py")
        if "__pycache__" not in path.parts
    )


@pytest.mark.parametrize("layer", sorted(FORBIDDEN_IMPORTS))
def test_layer_does_not_import_upper_layers(layer: str):
    forbidden = FORBIDDEN_IMPORTS[layer]
    violations: list[str] = []

    files = _python_files(layer)
    assert files, f"В слое {layer} не найдено ни одного модуля"

    for path in files:
        for module in _iter_imported_modules(path.read_text(encoding="utf-8")):
            if module.startswith(forbidden):
                rel = path.relative_to(BACK_DIR).as_posix()
                violations.append(f"{rel}: {module}")

    assert not violations, (
        f"Слой {layer} не имеет права знать о {', '.join(forbidden)}:\n"
        + "\n".join(violations)
    )
