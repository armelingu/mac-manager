"""Unit tests for the pure helpers inside `macmanager.doctor`."""

from __future__ import annotations

import pytest

from macmanager.doctor import _score


class TestScore:
    """`_score(value, ranges)` walks a "best -> worst" list and returns the
    first `points` whose `threshold <= value`. If no threshold matches,
    returns 0."""

    def test_returns_zero_when_no_threshold_matches(self) -> None:
        assert _score(-5, [(0, 10), (10, 5)]) == 0

    def test_returns_highest_tier_when_value_dominates(self) -> None:
        ranges = [(90, 25), (80, 20), (70, 12)]
        assert _score(100, ranges) == 25

    def test_returns_lowest_tier_when_value_just_qualifies(self) -> None:
        ranges = [(90, 25), (80, 20), (70, 12), (0, 0)]
        assert _score(0, ranges) == 0

    def test_threshold_is_inclusive(self) -> None:
        # Exactly-equal should still satisfy `value >= threshold`.
        ranges = [(90, 25), (80, 20)]
        assert _score(90, ranges) == 25
        assert _score(80, ranges) == 20

    def test_just_below_threshold_picks_next_tier(self) -> None:
        ranges = [(90, 25), (80, 20), (70, 12)]
        assert _score(89.9, ranges) == 20
        assert _score(79.9, ranges) == 12

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (100, 25),  # excellent
            (90, 25),  # boundary
            (85, 20),
            (75, 12),
            (65, 6),
            (50, 0),
            (0, 0),
        ],
    )
    def test_battery_health_scoring_matches_doctor_table(self, value: float, expected: int) -> None:
        """The doctor module uses `_score(bat.health_percent, [(90,25), ...])`.
        This test locks in that table as a contract."""
        ranges = [(90, 25), (80, 20), (70, 12), (60, 6), (0, 0)]
        assert _score(value, ranges) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (100, 20),  # fresh install, lots of space
            (30, 20),  # boundary
            (25, 15),
            (15, 8),
            (7, 3),
            (2, 0),
        ],
    )
    def test_free_disk_scoring_matches_doctor_table(self, value: float, expected: int) -> None:
        ranges = [(30, 20), (20, 15), (10, 8), (5, 3), (0, 0)]
        assert _score(value, ranges) == expected

    def test_empty_ranges_returns_zero(self) -> None:
        assert _score(100, []) == 0

    def test_single_range_behaves_predictably(self) -> None:
        ranges = [(50, 10)]
        assert _score(50, ranges) == 10
        assert _score(100, ranges) == 10
        assert _score(49, ranges) == 0
