"""
Тесты пула API-ключей: хранение, ротация и учет здоровья ключей.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.back.l01_domain.exceptions import LLMKeyMissingError
from src.back.l03_infrastructure.llm.keys.manager import (
    ApiKeyManager,
    ApiKeyStatus,
    PrimaryFirstRotation,
    mask_key,
)


class FrozenClock:
    """Управляемые часы: тесты кулдауна не должны зависеть от реального времени."""

    def __init__(self) -> None:
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)


class TestMasking:
    def test_long_key_shows_only_edges(self):
        assert mask_key("sk-proj-abcdefgh1234") == "sk-p...1234"

    def test_short_key_is_fully_hidden(self):
        assert mask_key("secret") == "******"


class TestPool:
    def test_blank_and_duplicate_keys_are_ignored(self):
        keys = ApiKeyManager()

        assert keys.add_key("openai", "  sk-1  ") is True
        assert keys.add_key("openai", "sk-1") is False
        assert keys.add_key("openai", "   ") is False
        assert len(keys.list_keys("openai")) == 1

    def test_set_keys_replaces_pool(self):
        keys = ApiKeyManager()
        keys.add_key("openai", "sk-old")

        accepted = keys.set_keys("openai", ["sk-a", "sk-b"])

        assert accepted == 2
        assert {view.masked_value for view in keys.list_keys("openai")} == {
            mask_key("sk-a"),
            mask_key("sk-b"),
        }

    def test_listing_never_exposes_the_secret(self):
        keys = ApiKeyManager()
        keys.add_key("openai", "sk-proj-supersecret-value")

        view = keys.list_keys("openai")[0]

        assert "supersecret" not in view.masked_value
        assert view.status is ApiKeyStatus.ACTIVE

    def test_key_is_removed_by_masked_value(self):
        keys = ApiKeyManager()
        keys.add_key("openai", "sk-proj-abcdefgh1234")

        assert keys.remove_key("openai", "sk-p...1234") is True
        assert keys.list_keys("openai") == []

    def test_env_fallback(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("HH_OPENAI_KEY", "sk-from-env")
        keys = ApiKeyManager()

        assert keys.load_from_env("openai", "HH_OPENAI_KEY") is True
        assert keys.get_key("openai") == "sk-from-env"

    def test_missing_env_var_is_not_an_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("HH_MISSING_KEY", raising=False)
        keys = ApiKeyManager()

        assert keys.load_from_env("openai", "HH_MISSING_KEY") is False
        assert keys.has_keys("openai") is False


class TestRotation:
    def test_round_robin_spreads_load(self):
        keys = ApiKeyManager()
        keys.set_keys("openai", ["sk-a", "sk-b", "sk-c"])

        assert [keys.get_key("openai") for _ in range(4)] == ["sk-a", "sk-b", "sk-c", "sk-a"]

    def test_primary_first_sticks_to_the_paid_key(self):
        keys = ApiKeyManager(rotation=PrimaryFirstRotation())
        keys.set_keys("openai", ["sk-paid", "sk-spare"])

        assert [keys.get_key("openai") for _ in range(3)] == ["sk-paid"] * 3

    def test_primary_first_falls_through_when_key_dies(self):
        keys = ApiKeyManager(rotation=PrimaryFirstRotation())
        keys.set_keys("openai", ["sk-paid", "sk-spare"])

        keys.report_rejected("openai", "sk-paid")

        assert keys.get_key("openai") == "sk-spare"

    def test_empty_pool_raises(self):
        with pytest.raises(LLMKeyMissingError):
            ApiKeyManager().get_key("openai")


class TestKeyHealth:
    def test_rejected_key_leaves_the_rotation(self):
        keys = ApiKeyManager()
        keys.set_keys("openai", ["sk-bad", "sk-good"])

        keys.report_rejected("openai", "sk-bad")

        assert [keys.get_key("openai") for _ in range(2)] == ["sk-good", "sk-good"]
        assert keys.list_keys("openai")[0].status is ApiKeyStatus.REVOKED

    def test_rate_limited_key_returns_after_cooldown(self):
        clock = FrozenClock()
        keys = ApiKeyManager(cooldown_seconds=300, clock=clock)
        keys.set_keys("openai", ["sk-a"])

        keys.report_rate_limited("openai", "sk-a")
        with pytest.raises(LLMKeyMissingError):
            keys.get_key("openai")

        clock.advance(301)

        assert keys.get_key("openai") == "sk-a"

    def test_success_heals_a_cooling_key(self):
        clock = FrozenClock()
        keys = ApiKeyManager(clock=clock)
        keys.set_keys("openai", ["sk-a"])

        keys.report_rate_limited("openai", "sk-a")
        keys.report_success("openai", "sk-a")

        assert keys.has_keys("openai") is True
        assert keys.list_keys("openai")[0].status is ApiKeyStatus.ACTIVE

    def test_feedback_about_unknown_key_is_ignored(self):
        keys = ApiKeyManager()

        keys.report_rejected("openai", "sk-never-added")

        assert keys.list_keys("openai") == []
