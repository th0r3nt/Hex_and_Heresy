"""
Тесты ротации API-ключей: Round-Robin, кулдауны по лимитам и бан мертвых ключей.
"""

import pytest

from src.back.l03_infrastructure.llm.keys.rotator import (
    AllKeysExhaustedError,
    APIKeyRotator,
)


class TestInitialization:
    def test_empty_pool_is_allowed_for_local_models(self):
        rotator = APIKeyRotator(provider_id="local", keys=[])

        assert rotator.total_keys() == 0
        assert rotator.get_next_key() is None

    def test_blank_keys_are_filtered_and_trimmed(self):
        rotator = APIKeyRotator(provider_id="openrouter", keys=["  sk-one  ", "", "   ", "sk-two"])

        assert rotator.keys == ["sk-one", "sk-two"]
        assert rotator.total_keys() == 2


class TestRoundRobin:
    def test_keys_are_handed_out_in_a_cycle(self):
        rotator = APIKeyRotator(provider_id="p", keys=["a", "b", "c"])

        issued = [rotator.get_next_key() for _ in range(6)]

        assert issued == ["a", "b", "c", "a", "b", "c"]

    def test_single_key_is_returned_every_time(self):
        rotator = APIKeyRotator(provider_id="p", keys=["only"])

        assert [rotator.get_next_key() for _ in range(3)] == ["only"] * 3


class TestCooldowns:
    def test_frozen_key_is_skipped(self, clock):
        rotator = APIKeyRotator(provider_id="p", keys=["a", "b"])
        rotator.cooldown_key("a", seconds=60)

        assert [rotator.get_next_key() for _ in range(3)] == ["b", "b", "b"]

    def test_key_returns_to_rotation_after_cooldown_expires(self, clock):
        rotator = APIKeyRotator(provider_id="p", keys=["a", "b"])
        rotator.cooldown_key("a", seconds=60)
        assert rotator.get_next_key() == "b"

        clock.advance(61)

        assert rotator.get_next_key() in {"a", "b"}
        assert set(rotator.get_next_key() for _ in range(4)) == {"a", "b"}

    def test_all_frozen_keys_raise_with_shortest_wait(self, clock):
        rotator = APIKeyRotator(provider_id="p", keys=["a", "b"])
        rotator.cooldown_key("a", seconds=120)
        rotator.cooldown_key("b", seconds=30)

        with pytest.raises(AllKeysExhaustedError) as exc_info:
            rotator.get_next_key()

        # Ждать нужно ровно до разморозки ближайшего ключа
        assert exc_info.value.wait_time == 30
        assert "30" in str(exc_info.value)

    def test_wait_time_is_never_below_one_second(self, clock):
        rotator = APIKeyRotator(provider_id="p", keys=["a"])
        rotator.cooldown_key("a", seconds=10)
        clock.advance(9.9)

        with pytest.raises(AllKeysExhaustedError) as exc_info:
            rotator.get_next_key()

        assert exc_info.value.wait_time == 1

    def test_cooldown_of_unknown_key_is_ignored(self, clock):
        rotator = APIKeyRotator(provider_id="p", keys=["a"])

        rotator.cooldown_key("ghost", seconds=60)

        assert rotator.get_next_key() == "a"

    def test_empty_pool_returns_none_instead_of_raising(self, clock):
        rotator = APIKeyRotator(provider_id="local", keys=[])

        assert rotator.get_next_key() is None


class TestBanning:
    def test_banned_key_leaves_the_pool(self):
        rotator = APIKeyRotator(provider_id="p", keys=["a", "b"])

        rotator.ban_key("a")

        assert rotator.total_keys() == 1
        assert [rotator.get_next_key() for _ in range(3)] == ["b", "b", "b"]

    def test_banning_unknown_key_is_ignored(self):
        rotator = APIKeyRotator(provider_id="p", keys=["a"])

        rotator.ban_key("ghost")

        assert rotator.total_keys() == 1

    def test_index_stays_valid_after_ban_of_last_key(self):
        rotator = APIKeyRotator(provider_id="p", keys=["a", "b", "c"])
        rotator.get_next_key()  # a, курсор -> 1
        rotator.get_next_key()  # b, курсор -> 2

        rotator.ban_key("c")

        # Курсор пересчитан по новой длине пула: IndexError быть не должно
        assert rotator.get_next_key() == "a"

    def test_banning_all_keys_empties_the_pool(self):
        rotator = APIKeyRotator(provider_id="p", keys=["a", "b"])

        rotator.ban_key("a")
        rotator.ban_key("b")

        assert rotator.total_keys() == 0
        assert rotator.get_next_key() is None

    def test_banned_key_frees_its_cooldown_slot(self, clock):
        rotator = APIKeyRotator(provider_id="p", keys=["a", "b"])
        rotator.cooldown_key("a", seconds=600)

        rotator.ban_key("a")

        assert "a" not in rotator._cooldowns
        assert rotator.get_next_key() == "b"
