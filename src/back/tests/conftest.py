"""
Общие фикстуры всего набора тестов бэкэнда.
"""

import pytest

from src.back.l03_infrastructure.gamedata.loader import (
    StaticGameDataRegistry,
    build_static_registry,
)


@pytest.fixture(scope="session")
def static_registry() -> StaticGameDataRegistry:
    """
    Настоящие каталоги геймдаты, собранные один раз на весь прогон.

    Реестр read-only, а сканирование пакетов - самая дорогая часть сборки,
    поэтому пересобирать его на каждый тест незачем.
    """
    return build_static_registry()
