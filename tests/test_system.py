"""Unit tests for the pure helpers inside `macmanager.system`."""

from __future__ import annotations

import pytest

from macmanager.system import _pressure_color


class TestPressureColor:
    """`_pressure_color(state)` translates the vm_stat pressure state into a
    Rich color. Known states come from `vm_stat` / Activity Monitor:
    Normal / Warn / Critical. Anything else (including "Unknown" or a
    typo) falls back to `dim`."""

    @pytest.mark.parametrize(
        ("state", "color"),
        [
            ("Normal", "green"),
            ("Warn", "yellow"),
            ("Critical", "red"),
        ],
    )
    def test_known_states(self, state: str, color: str) -> None:
        assert _pressure_color(state) == color

    @pytest.mark.parametrize("state", ["Unknown", "", "warn", "normal", "random"])
    def test_unknown_states_fall_back_to_dim(self, state: str) -> None:
        # Case-sensitive on purpose — the source dict is keyed on exact strings.
        assert _pressure_color(state) == "dim"
