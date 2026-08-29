"""
Окружение тестов генератора мира.

Генератор работает по настоящим каталогам геймдаты: подменять их фейком
бессмысленно, потому что половина его работы - это как раз выбор зданий,
рецептов найма и правителей из реальных реестров.
"""

from typing import Callable

import pytest

from src.back.l01_domain.common import FactionRace
from src.back.l01_domain.world.models.setup import (
    FactionSetupConfig,
    NewGameConfig,
)
from src.back.l02_services.mechanics.vision.facade import VisionFacade
from src.back.l02_services.world.generator import WorldGenerator
from src.back.l03_infrastructure.gamedata.loader import StaticGameDataRegistry

# Сид, на котором написаны проверки раскладки карты
DEFAULT_TEST_SEED = 20260829


@pytest.fixture
def generator(static_registry: StaticGameDataRegistry) -> WorldGenerator:
    """Генератор с настоящей геймдатой и живым расчетом тумана войны."""
    return WorldGenerator(gamedata=static_registry, vision_facade=VisionFacade())


@pytest.fixture
def make_config() -> Callable[..., NewGameConfig]:
    """
    Фабрика настроек партии: люди против зеленокожих плюс баронства.

    Любое поле перебивается именованным аргументом, поэтому тест пишет
    только то, что действительно проверяет.
    """

    def _make(**overrides) -> NewGameConfig:
        defaults = {
            "seed": DEFAULT_TEST_SEED,
            "player_faction": FactionSetupConfig(
                race=FactionRace.HUMANS, name="Империя", is_player_controlled=True
            ),
            "rival_faction": FactionSetupConfig(
                race=FactionRace.GREENSKINS, name="Орда"
            ),
        }
        return NewGameConfig(**{**defaults, **overrides})

    return _make
