"""Unit tests for the pure helpers inside `macmanager.system`."""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console

from macmanager.system import SystemInfo, _pressure_color, render_system_panel


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


class TestRenderSystemPanel:
    """Nome de processo com `[/]` não pode derrubar `mm health`."""

    def test_process_name_with_markup_does_not_raise(self) -> None:
        info = SystemInfo(
            cpu_percent=10.0,
            load_avg_1=1.0,
            load_avg_5=1.0,
            load_avg_15=1.0,
            cpu_count=8,
            memory_total=16 * 1024**3,
            memory_used=8 * 1024**3,
            memory_percent=50.0,
            swap_used=0,
            swap_total=0,
            memory_pressure="Normal",
            uptime_sec=1000,
            top_processes=[{"pid": 1, "name": "foo[/]bar", "cpu": 10.0, "mem": 1000}],
        )
        buf = StringIO()
        Console(file=buf, force_terminal=True, width=80).print(render_system_panel(info))
        assert "foo" in buf.getvalue()
