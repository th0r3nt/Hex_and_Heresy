"""
Общие фикстуры сервисного слоя: доменные фейки сборщиков промптов и контекста.
"""

import pytest

from src.back.tests.l02_services.fakes import FakeContextBuilder, FakePromptBuilder


@pytest.fixture
def fake_prompt_builder() -> FakePromptBuilder:
    return FakePromptBuilder()


@pytest.fixture
def fake_context_builder() -> FakeContextBuilder:
    return FakeContextBuilder()
