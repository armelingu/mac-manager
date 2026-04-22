"""Unit tests for the pure helpers inside `macmanager.battery`."""

from __future__ import annotations

from dataclasses import fields

import pytest

from macmanager.battery import BatteryInfo, cycle_color


class TestCycleColor:
    """`cycle_color(cycles)` buckets the lifetime charge cycle count into a
    Rich color. Apple lists 1000 cycles as the modern-Mac lifespan, so the
    thresholds are:

        cycles < 300  -> green  (plenty of life left)
        cycles < 700  -> yellow
        else          -> red    (close to end of life)
    """

    @pytest.mark.parametrize("cycles", [0, 1, 299])
    def test_green_under_300(self, cycles: int) -> None:
        assert cycle_color(cycles) == "green"

    @pytest.mark.parametrize("cycles", [300, 500, 699])
    def test_yellow_between_300_and_700(self, cycles: int) -> None:
        assert cycle_color(cycles) == "yellow"

    @pytest.mark.parametrize("cycles", [700, 999, 1500])
    def test_red_at_or_above_700(self, cycles: int) -> None:
        assert cycle_color(cycles) == "red"


class TestBatteryInfo:
    """`BatteryInfo` is a data snapshot. This lightweight contract test
    guards the field list from accidental removals / renames that would
    silently break the CSV logger + doctor scoring."""

    def test_has_expected_fields(self) -> None:
        expected = {
            "percent",
            "is_charging",
            "power_source",
            "time_remaining_sec",
            "cycle_count",
            "max_capacity_mah",
            "design_capacity_mah",
            "health_percent",
            "temperature_c",
            "fully_charged",
            "serial",
        }
        actual = {f.name for f in fields(BatteryInfo)}
        # Use subset: extra fields are fine (forward-compatible), missing
        # ones are a breaking change.
        assert expected.issubset(actual), f"missing fields: {expected - actual}"
