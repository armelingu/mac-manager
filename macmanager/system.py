"""System metrics: CPU, RAM, processes, uptime, mem pressure."""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from typing import Optional

import psutil
from rich.panel import Panel
from rich.table import Table

from macmanager.cache import cached
from macmanager.ui import bar, console, fmt_bytes, fmt_seconds, usage_color


@dataclass
class SystemInfo:
    cpu_percent: float
    load_avg_1: float
    load_avg_5: float
    load_avg_15: float
    cpu_count: int
    memory_total: int
    memory_used: int
    memory_percent: float
    swap_used: int
    swap_total: int
    memory_pressure: str           # Normal | Warn | Critical | Unknown
    uptime_sec: int
    top_processes: list[dict]


@cached(ttl=10)
def _memory_pressure() -> str:
    try:
        out = subprocess.run(
            ["memory_pressure"],
            capture_output=True, text=True, timeout=2,
        ).stdout
    except Exception:
        return "Unknown"
    m = re.search(r"System-wide memory free percentage:\s*(\d+)%", out)
    if not m:
        return "Unknown"
    free = int(m.group(1))
    if free >= 30:
        return "Normal"
    if free >= 10:
        return "Warn"
    return "Critical"


@cached(ttl=5)
def _top_processes(limit: int = 5) -> list[dict]:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            procs.append({
                "pid": p.info["pid"],
                "name": p.info["name"] or "—",
                "cpu": p.info["cpu_percent"] or 0.0,
                "mem": (p.info["memory_info"].rss if p.info["memory_info"] else 0),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: (x["cpu"], x["mem"]), reverse=True)
    return procs[:limit]


def get_system(quick: bool = False) -> SystemInfo:
    # cpu_percent needs an interval to be accurate on the 1st call
    cpu = psutil.cpu_percent(interval=0 if quick else 0.5)
    vm = psutil.virtual_memory()
    try:
        sw = psutil.swap_memory()
        swap_used, swap_total = sw.used, sw.total
    except (OSError, RuntimeError):
        swap_used = swap_total = 0
    try:
        l1, l5, l15 = psutil.getloadavg()
    except (AttributeError, OSError):
        l1 = l5 = l15 = 0.0

    return SystemInfo(
        cpu_percent=cpu,
        load_avg_1=l1, load_avg_5=l5, load_avg_15=l15,
        cpu_count=psutil.cpu_count(logical=True) or 0,
        memory_total=vm.total,
        memory_used=vm.total - vm.available,
        memory_percent=vm.percent,
        swap_used=swap_used,
        swap_total=swap_total,
        memory_pressure=_memory_pressure(),
        uptime_sec=int(time.time() - psutil.boot_time()),
        top_processes=[] if quick else _top_processes(),
    )


def _pressure_color(state: str) -> str:
    return {"Normal": "green", "Warn": "yellow", "Critical": "red"}.get(state, "dim")


def render_system_panel(info: Optional[SystemInfo] = None) -> Panel:
    info = info or get_system()

    t = Table.grid(padding=(0, 1))
    t.add_column(justify="right", style="dim")
    t.add_column()

    t.add_row(
        "CPU",
        f"[{usage_color(info.cpu_percent)}]{info.cpu_percent:5.1f}%[/]  "
        f"{bar(info.cpu_percent)}  [dim]· {info.cpu_count} cores[/]",
    )
    t.add_row(
        "Load avg",
        f"{info.load_avg_1:.2f}  {info.load_avg_5:.2f}  {info.load_avg_15:.2f}  [dim](1·5·15 min)[/]",
    )
    t.add_row(
        "RAM",
        f"[{usage_color(info.memory_percent)}]{info.memory_percent:5.1f}%[/]  "
        f"{bar(info.memory_percent)}  "
        f"[dim]{fmt_bytes(info.memory_used)} / {fmt_bytes(info.memory_total)}[/]",
    )
    t.add_row(
        "Mem pressure",
        f"[{_pressure_color(info.memory_pressure)}]{info.memory_pressure}[/]",
    )
    if info.swap_total:
        swap_pct = (info.swap_used / info.swap_total) * 100 if info.swap_total else 0
        t.add_row(
            "Swap",
            f"[{usage_color(swap_pct, 30, 60)}]{fmt_bytes(info.swap_used)}[/] / {fmt_bytes(info.swap_total)}",
        )
    t.add_row("Uptime", fmt_seconds(info.uptime_sec))

    if info.top_processes:
        t.add_row("", "")
        t.add_row("[bold]Top processes[/]", "")
        for p in info.top_processes:
            t.add_row(
                f"[dim]{p['pid']:>5}[/] {p['name'][:25]}",
                f"CPU [bold]{p['cpu']:5.1f}%[/]  MEM [bold]{fmt_bytes(p['mem'])}[/]",
            )

    return Panel(t, title="[bold]System[/]", border_style="magenta")


def cmd_health(args=None) -> None:
    console.print(render_system_panel())
