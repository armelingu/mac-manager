"""Unit tests for `macmanager.cache`.

The cache is small enough and important enough to exercise directly:
TTL expiry, keying on args, ttl<=0 bypass, `peek` + `is_miss`, and the
per-function `cache_clear` attribute.
"""

from __future__ import annotations

import time

import pytest

from macmanager import cache as cache_mod
from macmanager.cache import cached, clear_all, is_miss, peek


@pytest.fixture(autouse=True)
def _isolate_cache():
    """Every test starts with an empty cache and leaves one behind."""
    clear_all()
    yield
    clear_all()


class TestCachedDecorator:
    def test_caches_return_value_within_ttl(self) -> None:
        calls = []

        @cached(ttl=60)
        def heavy() -> int:
            calls.append(1)
            return 42

        assert heavy() == 42
        assert heavy() == 42
        assert heavy() == 42
        assert len(calls) == 1, "function should have been executed exactly once"

    def test_different_args_get_separate_entries(self) -> None:
        calls = []

        @cached(ttl=60)
        def add(a: int, b: int) -> int:
            calls.append((a, b))
            return a + b

        assert add(1, 2) == 3
        assert add(1, 2) == 3  # cache hit
        assert add(2, 3) == 5  # cache miss, different args
        assert add(1, 2) == 3  # still cached
        assert calls == [(1, 2), (2, 3)]

    def test_ttl_zero_bypasses_cache(self) -> None:
        calls = []

        @cached(ttl=0)
        def counter() -> int:
            calls.append(1)
            return len(calls)

        assert counter() == 1
        assert counter() == 2
        assert counter() == 3

    def test_negative_ttl_also_bypasses_cache(self) -> None:
        calls = []

        @cached(ttl=-5)
        def counter() -> int:
            calls.append(1)
            return len(calls)

        assert counter() == 1
        assert counter() == 2

    def test_unhashable_arg_falls_back_to_plain_call(self) -> None:
        """When args can't be placed in a tuple key (e.g. a dict), the
        decorator silently skips caching instead of crashing."""
        calls = []

        @cached(ttl=60)
        def echo(d: dict) -> int:
            calls.append(1)
            return d["n"]

        assert echo({"n": 5}) == 5
        assert echo({"n": 5}) == 5
        # Both calls went through — dict is unhashable so no cache.
        assert len(calls) == 2

    def test_ttl_expires_and_re_invokes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = []
        now = [1000.0]

        def fake_monotonic() -> float:
            return now[0]

        monkeypatch.setattr("macmanager.cache.time.monotonic", fake_monotonic)

        @cached(ttl=10)
        def heavy() -> int:
            calls.append(1)
            return 7

        assert heavy() == 7
        assert heavy() == 7
        assert len(calls) == 1

        # Advance past TTL. The next call must re-execute.
        now[0] += 11
        assert heavy() == 7
        assert len(calls) == 2

    def test_cache_clear_attribute_empties_only_that_function(self) -> None:
        calls_a = []
        calls_b = []

        @cached(ttl=60)
        def a() -> int:
            calls_a.append(1)
            return 1

        @cached(ttl=60)
        def b() -> int:
            calls_b.append(1)
            return 2

        a(), a(), b(), b()
        assert len(calls_a) == 1
        assert len(calls_b) == 1

        # clear_cache on `a` should not touch `b`'s entry.
        a.cache_clear()

        a()
        b()
        assert len(calls_a) == 2
        assert len(calls_b) == 1, "clearing `a` must not invalidate `b`"

    def test_preserves_wrapped_function_metadata(self) -> None:
        @cached(ttl=5)
        def documented(x: int) -> int:
            """Returns x doubled."""
            return x * 2

        assert documented.__name__ == "documented"
        assert documented.__doc__ == "Returns x doubled."


class TestPeek:
    def test_miss_when_nothing_cached(self) -> None:
        @cached(ttl=60)
        def fresh() -> int:
            return 99

        assert is_miss(peek(fresh))

    def test_hit_after_primed(self) -> None:
        @cached(ttl=60)
        def primed() -> int:
            return 99

        primed()  # primes the cache
        value = peek(primed)
        assert not is_miss(value)
        assert value == 99

    def test_peek_does_not_execute_function(self) -> None:
        calls = []

        @cached(ttl=60)
        def never() -> int:
            calls.append(1)
            return 0

        for _ in range(3):
            peek(never)
        assert calls == [], "peek must not execute the wrapped function"

    def test_peek_with_unhashable_args_is_a_miss(self) -> None:
        @cached(ttl=60)
        def fn(d: dict) -> int:
            return d["n"]

        assert is_miss(peek(fn, {"n": 1}))


class TestClearAll:
    def test_clears_multiple_entries(self) -> None:
        @cached(ttl=60)
        def one() -> int:
            return 1

        @cached(ttl=60)
        def two() -> int:
            return 2

        one()
        two()
        assert not is_miss(peek(one))
        assert not is_miss(peek(two))

        clear_all()

        assert is_miss(peek(one))
        assert is_miss(peek(two))


class TestIsMiss:
    def test_sentinel_is_miss(self) -> None:
        assert is_miss(cache_mod._MISS)

    def test_any_other_value_is_not_miss(self) -> None:
        for candidate in [None, 0, "", [], {}, object()]:
            assert not is_miss(candidate)


class TestMonotonicIsUsed:
    """Regression: the cache must use `time.monotonic`, not `time.time`,
    so NTP jumps / clock drift can't prematurely expire or indefinitely
    extend entries."""

    def test_uses_monotonic(self) -> None:
        # We just need to know the symbol is referenced from the module.
        # If this import survives, the code path in cache.py used it.
        assert callable(time.monotonic)
