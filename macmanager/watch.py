"""Live dashboard with rich.live — refreshes everything in a single panel.

Layout:
    ┌─────────── header ───────────┐
    │ battery     │ system         │
    │ disk        │ network        │
    ├─────── health bar ───────────┤  (compact: doctor + security + updates)
    │           footer             │
    └──────────────────────────────┘

Heavy collections (security, doctor) are cached in the background to avoid
blocking the redraw — see `macmanager.cache`.
"""

from __future__ import annotations

import contextlib
import threading
import time
from datetime import datetime

from rich.align import Align
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from macmanager.battery import render_battery_panel
from macmanager.cache import is_miss, peek
from macmanager.disk import render_disk_panel
from macmanager.doctor import doctor as run_doctor
from macmanager.network import render_network_panel
from macmanager.security import check_macos_updates
from macmanager.security import run_all as run_security
from macmanager.system import render_system_panel
from macmanager.ui import console, health_color


def _build_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="health", size=3),
        Layout(name="footer", size=1),
    )
    layout["body"].split_row(Layout(name="left"), Layout(name="right"))
    layout["left"].split_column(Layout(name="battery"), Layout(name="disk"))
    layout["right"].split_column(Layout(name="system"), Layout(name="network"))
    return layout


_LOADING = "[dim italic]loading...[/]"


def _render_health_bar() -> Panel:
    """Single line with aggregated KPIs: doctor score + security + updates.

    Uses `peek` on the cache so the redraw isn't blocked — if there's no
    cached value yet (background warm-up), shows "loading...".
    """
    d = peek(run_doctor)
    if is_miss(d):
        doctor_str = _LOADING
    else:
        try:
            score = d["score"]
            score_color = health_color(score, good=85, warn=65)
            doctor_str = f"[{score_color}]{score:.0f}/100[/]"
        except Exception:
            doctor_str = "[dim]?[/]"

    checks = peek(run_security)
    if is_miss(checks):
        sec_str = _LOADING
    else:
        try:
            fails = sum(1 for c in checks if c.status == "FAIL")
            warns = sum(1 for c in checks if c.status == "WARN")
            if fails:
                sec_str = f"[red]{fails} FAIL[/]"
                if warns:
                    sec_str += f" [yellow]· {warns} WARN[/]"
            elif warns:
                sec_str = f"[yellow]{warns} WARN[/]"
            else:
                sec_str = "[green]OK[/]"
        except Exception:
            sec_str = "[dim]?[/]"

    upd = peek(check_macos_updates)
    if is_miss(upd):
        upd_str = _LOADING
    else:
        try:
            if upd.status == "OK":
                upd_str = "[green]none[/]"
            elif upd.status == "WARN":
                count = upd.detail.split(" ")[0]
                upd_str = f"[yellow]{count} pending[/]"
            else:
                upd_str = f"[dim]{upd.detail}[/]"
        except Exception:
            upd_str = "[dim]?[/]"

    t = Table.grid(expand=True, padding=(0, 2))
    t.add_column(justify="center", ratio=1)
    t.add_column(justify="center", ratio=1)
    t.add_column(justify="center", ratio=1)
    t.add_row(
        f"[bold]Doctor[/] {doctor_str}",
        f"[bold]Security[/] {sec_str}",
        f"[bold]macOS updates[/] {upd_str}",
    )
    return Panel(t, title="[bold]Overall health[/]", border_style="yellow")


def _render(layout: Layout) -> Layout:
    now = datetime.now().strftime("%a %d/%m %H:%M:%S")
    header = Panel(
        Align.center(Text(f"Mac Manager — Live dashboard  ·  {now}", style="bold cyan")),
        border_style="cyan",
    )
    layout["header"].update(header)
    layout["battery"].update(render_battery_panel())
    layout["system"].update(render_system_panel())
    layout["disk"].update(render_disk_panel(full=False))
    layout["network"].update(render_network_panel())
    layout["health"].update(_render_health_bar())
    layout["footer"].update(
        Align.center(Text("Press Ctrl+C to exit  ·  health bar refreshes every ~5min", style="dim"))
    )
    return layout


_HEAVY_COLLECTORS = (run_doctor, run_security, check_macos_updates)


def _warm_cache_background() -> None:
    """Pre-warms heavy collections in parallel. Each one populates its own cache.
    Errors are silenced — render uses "?" fallback if it fails."""

    def _safe(fn):
        with contextlib.suppress(Exception):
            fn()

    for fn in _HEAVY_COLLECTORS:
        threading.Thread(target=_safe, args=(fn,), daemon=True).start()


def cmd_watch(args=None) -> None:
    interval = getattr(args, "interval", 2) if args else 2
    _warm_cache_background()
    layout = _build_layout()
    try:
        with Live(_render(layout), refresh_per_second=4, screen=True, console=console) as live:
            while True:
                time.sleep(interval)
                live.update(_render(layout))
    except KeyboardInterrupt:
        console.print("\n[dim]Exiting dashboard.[/]")
