"""Testes do dispatcher e do status isolado.

Não exercitamos coletores reais (ioreg/psutil) — o CI roda em Linux.
Aqui o contrato é: um painel morto não aborta o `mm` status.
"""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console
from rich.panel import Panel

from macmanager.cli import cmd_status


class TestCmdStatusIsolation:
    def test_survives_when_one_panel_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "macmanager.battery.render_battery_panel",
            lambda: Panel("bat", title="Battery"),
        )
        monkeypatch.setattr(
            "macmanager.system.render_system_panel",
            lambda: Panel("sys", title="System"),
        )
        monkeypatch.setattr(
            "macmanager.disk.render_disk_panel",
            lambda full=False: Panel("disk", title="Disk"),
        )

        def boom() -> Panel:
            raise TimeoutError("system_profiler")

        monkeypatch.setattr("macmanager.network.render_network_panel", boom)

        buf = StringIO()
        monkeypatch.setattr(
            "macmanager.ui.console",
            Console(file=buf, force_terminal=True, width=80),
        )

        cmd_status()
        out = buf.getvalue()
        assert "bat" in out
        assert "sys" in out
        assert "disk" in out
        assert "Não foi possível coletar estes dados" in out
