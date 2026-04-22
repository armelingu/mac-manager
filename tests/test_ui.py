"""Unit tests for `macmanager.ui` — pure formatters and color helpers.

These functions don't touch the terminal or Rich's I/O; they all return
plain strings. So we assert on the output directly.
"""

from __future__ import annotations

import pytest

from macmanager.ui import bar, fmt_bytes, fmt_seconds, health_color, usage_color

# ---------------------------------------------------------------------------
# fmt_bytes
# ---------------------------------------------------------------------------


class TestFmtBytes:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, "0.0 B"),
            (512, "512.0 B"),
            (1023, "1023.0 B"),
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024**3, "1.0 GB"),
            (1024**4, "1.0 TB"),
            (1024**5, "1.0 PB"),
        ],
    )
    def test_scales_across_units(self, value: int, expected: str) -> None:
        assert fmt_bytes(value) == expected

    def test_fractional_kb(self) -> None:
        # 1536 bytes = 1.5 KB
        assert fmt_bytes(1536) == "1.5 KB"

    def test_negative_values_are_handled(self) -> None:
        # abs() is used for the comparison, so small negatives keep the
        # B unit and display as-is.
        assert fmt_bytes(-512) == "-512.0 B"

    def test_very_large_numbers_fall_back_to_pb(self) -> None:
        # 2 PB should render in PB with the current loop exiting.
        result = fmt_bytes(2 * 1024**5)
        assert result.endswith(" PB")
        assert result == "2.0 PB"


# ---------------------------------------------------------------------------
# fmt_seconds
# ---------------------------------------------------------------------------


class TestFmtSeconds:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, "0s"),
            (5, "5s"),
            (59, "59s"),
            (60, "1m 00s"),
            (125, "2m 05s"),
            (3599, "59m 59s"),
            (3600, "1h 00m"),
            (3661, "1h 01m"),
            (7200, "2h 00m"),
        ],
    )
    def test_common_durations(self, value: int, expected: str) -> None:
        assert fmt_seconds(value) == expected

    @pytest.mark.parametrize("value", [-1, -60, -3600])
    def test_negative_returns_em_dash(self, value: int) -> None:
        assert fmt_seconds(value) == "—"

    def test_float_is_truncated_to_int(self) -> None:
        assert fmt_seconds(90.9) == "1m 30s"

    def test_none_returns_em_dash(self) -> None:
        # Signature technically is `int | float`, but the function has an
        # explicit `if secs is None` guard. Accept None at runtime.
        assert fmt_seconds(None) == "—"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# health_color / usage_color
# ---------------------------------------------------------------------------


class TestHealthColor:
    @pytest.mark.parametrize(
        ("pct", "expected"),
        [
            (100, "green"),
            (80, "green"),
            (79.9, "yellow"),
            (60, "yellow"),
            (59.9, "red"),
            (0, "red"),
        ],
    )
    def test_default_thresholds(self, pct: float, expected: str) -> None:
        assert health_color(pct) == expected

    def test_custom_thresholds(self) -> None:
        # Doctor uses good=85, warn=65.
        assert health_color(90, good=85, warn=65) == "green"
        assert health_color(70, good=85, warn=65) == "yellow"
        assert health_color(50, good=85, warn=65) == "red"


class TestUsageColor:
    @pytest.mark.parametrize(
        ("pct", "expected"),
        [
            (0, "green"),
            (69.9, "green"),
            (70, "yellow"),
            (89.9, "yellow"),
            (90, "red"),
            (100, "red"),
        ],
    )
    def test_default_thresholds(self, pct: float, expected: str) -> None:
        assert usage_color(pct) == expected


# ---------------------------------------------------------------------------
# bar
# ---------------------------------------------------------------------------


class TestBar:
    def test_empty_bar_at_zero(self) -> None:
        result = bar(0, width=10)
        # 0% -> 0 filled blocks, 10 empty blocks, wrapped in color tags.
        assert "█" not in result
        assert "░" * 10 in result
        assert result.startswith("[")
        assert result.endswith("[/]")

    def test_full_bar_at_hundred(self) -> None:
        result = bar(100, width=10)
        assert "█" * 10 in result
        assert "░" not in result

    def test_half_bar(self) -> None:
        result = bar(50, width=10)
        assert "█" * 5 in result
        assert "░" * 5 in result

    def test_clamps_above_hundred(self) -> None:
        assert bar(150, width=10) == bar(100, width=10)

    def test_clamps_below_zero(self) -> None:
        assert bar(-30, width=10) == bar(0, width=10)

    def test_uses_usage_color_by_default(self) -> None:
        # At 80% usage, the color should be yellow (from usage_color).
        result = bar(80, width=10)
        assert "[yellow]" in result

    def test_explicit_color_overrides_usage_color(self) -> None:
        result = bar(80, width=10, color="magenta")
        assert "[magenta]" in result
        assert "[yellow]" not in result

    def test_total_width_is_respected(self) -> None:
        for pct in (0, 25, 50, 75, 100):
            result = bar(pct, width=20)
            # Strip the color tags, count the bar glyphs.
            glyphs = result.replace("[/]", "")
            # Remove leading [color] segment.
            glyphs = glyphs.split("]", 1)[1]
            assert len(glyphs) == 20
