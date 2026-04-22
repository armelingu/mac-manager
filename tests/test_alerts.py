"""Tests for `macmanager.alerts` business-rule constants and `_can_fire`.

`_can_fire` uses `time.time()`, so we drive it via `monkeypatch`.

We also pin the threshold / cooldown values: these are not just
implementation details, they're the product contract shipped to users.
Changing HIGH from 80 to 85 silently would meaningfully change the
user experience.
"""

from __future__ import annotations

import pytest

from macmanager.alerts import COOLDOWNS, CRITICAL, HEALTH_WARN, HIGH, LOW, _can_fire


class TestThresholdValues:
    @pytest.mark.parametrize(
        ("name", "actual", "expected"),
        [
            ("HIGH", HIGH, 80),
            ("LOW", LOW, 20),
            ("CRITICAL", CRITICAL, 10),
            ("HEALTH_WARN", HEALTH_WARN, 80),
        ],
    )
    def test_pinned_threshold(self, name: str, actual: int, expected: int) -> None:
        assert actual == expected, f"{name} changed — update the product docs"

    def test_thresholds_are_ordered_correctly(self) -> None:
        assert CRITICAL < LOW < HIGH
        assert 0 < CRITICAL < 100
        assert 0 < LOW < 100
        assert 0 < HIGH < 100


class TestCooldowns:
    def test_has_entries_for_every_alert_kind(self) -> None:
        assert set(COOLDOWNS.keys()) == {"high", "low", "critical", "health"}

    def test_values_are_positive_seconds(self) -> None:
        for name, value in COOLDOWNS.items():
            assert isinstance(value, int)
            assert value > 0, f"cooldown {name!r} must be > 0 seconds"

    def test_critical_cooldown_is_shortest(self) -> None:
        # We want to nag the user aggressively when the battery is about
        # to die, less frequently otherwise.
        assert COOLDOWNS["critical"] <= COOLDOWNS["low"]
        assert COOLDOWNS["critical"] <= COOLDOWNS["high"]

    def test_health_cooldown_is_longest(self) -> None:
        # Health degrades slowly, so we only nag once a week.
        assert COOLDOWNS["health"] >= COOLDOWNS["high"]
        assert COOLDOWNS["health"] >= 60 * 60 * 24, "health cooldown should be >= 1 day"


class TestCanFire:
    def test_fires_when_no_previous_entry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("macmanager.alerts.time.time", lambda: 10_000.0)
        state: dict = {}
        assert _can_fire(state, "high", cooldown=60) is True

    def test_blocks_if_fired_within_cooldown(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("macmanager.alerts.time.time", lambda: 10_030.0)
        state = {"high": 10_000.0}  # fired 30s ago
        assert _can_fire(state, "high", cooldown=60) is False

    def test_allows_once_cooldown_elapses(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("macmanager.alerts.time.time", lambda: 10_100.0)
        state = {"high": 10_000.0}  # fired 100s ago, cooldown 60s -> should fire
        assert _can_fire(state, "high", cooldown=60) is True

    def test_boundary_exactly_at_cooldown_does_not_fire(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # `_can_fire` uses strict `>`, not `>=`. Lock that in.
        monkeypatch.setattr("macmanager.alerts.time.time", lambda: 10_060.0)
        state = {"high": 10_000.0}
        assert _can_fire(state, "high", cooldown=60) is False

    def test_independent_keys_dont_interfere(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("macmanager.alerts.time.time", lambda: 10_000.0)
        state = {"high": 9_999.0}
        # high is on cooldown, but low/critical have never fired.
        assert _can_fire(state, "high", cooldown=60) is False
        assert _can_fire(state, "low", cooldown=60) is True
        assert _can_fire(state, "critical", cooldown=60) is True
