"""Overall Mac health score + automatic recommendations."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table

from macmanager.battery import get_battery
from macmanager.cache import cached
from macmanager.disk import get_disk
from macmanager.system import get_system
from macmanager.ui import console, health_color


def _score(value: float, ranges: list[tuple[float, int]]) -> int:
    """For each (threshold, points), returns the first score whose threshold is met.
    Ranges should be ordered from best to worst case."""
    for threshold, points in ranges:
        if value >= threshold:
            return points
    return 0


@cached(ttl=15)
def doctor() -> dict:
    bat = get_battery()
    sys = get_system(quick=True)
    disk = get_disk(scan_cleanup=False)

    checks = []

    # Battery health (weight 25)
    bat_score = _score(bat.health_percent, [(90, 25), (80, 20), (70, 12), (60, 6), (0, 0)])
    checks.append({
        "name": "Battery health",
        "value": f"{bat.health_percent:.1f}%",
        "score": bat_score, "max": 25,
        "tip": (
            "Keep the charge between 20-80% day-to-day and enable 'Optimized Charging'."
            if bat.health_percent < 90 else "Excellent — keep it up."
        ),
    })

    # Cycles (weight 15)
    cyc_score = _score(1000 - bat.cycle_count, [(800, 15), (500, 12), (300, 8), (100, 4), (0, 0)])
    checks.append({
        "name": "Charge cycles",
        "value": f"{bat.cycle_count} / 1000",
        "score": cyc_score, "max": 15,
        "tip": "Every cycle counts — avoid frequent deep discharges." if bat.cycle_count > 300 else "Plenty of life left.",
    })

    # Free disk (weight 20)
    free_pct = (disk.free / disk.total) * 100 if disk.total else 0
    disk_score = _score(free_pct, [(30, 20), (20, 15), (10, 8), (5, 3), (0, 0)])
    checks.append({
        "name": "Free disk space",
        "value": f"{free_pct:.1f}%",
        "score": disk_score, "max": 20,
        "tip": "Run `mm clean` to see cleanup candidates." if free_pct < 20 else "Healthy space.",
    })

    # Memory pressure (weight 20)
    mem_map = {"Normal": 20, "Warn": 10, "Critical": 0, "Unknown": 15}
    mem_score = mem_map.get(sys.memory_pressure, 15)
    checks.append({
        "name": "Memory pressure",
        "value": sys.memory_pressure,
        "score": mem_score, "max": 20,
        "tip": (
            "Close heavy apps or refresh the natural swap by rebooting the Mac."
            if sys.memory_pressure in ("Warn", "Critical") else "Memory breathing well."
        ),
    })

    # CPU (weight 10)
    cpu_score = _score(100 - sys.cpu_percent, [(70, 10), (50, 7), (30, 4), (10, 1), (0, 0)])
    checks.append({
        "name": "Current CPU load",
        "value": f"{sys.cpu_percent:.1f}%",
        "score": cpu_score, "max": 10,
        "tip": "High CPU — check `mm health` to see the offender." if sys.cpu_percent > 70 else "All quiet.",
    })

    # Battery temperature (weight 10)
    if bat.temperature_c is not None:
        if bat.temperature_c < 35:
            temp_score, temp_tip = 10, "Optimal temperature."
        elif bat.temperature_c < 40:
            temp_score, temp_tip = 6, "Heating up — watch background apps."
        else:
            temp_score, temp_tip = 2, "Hot! Avoid heavy use while charging."
        checks.append({
            "name": "Battery temperature",
            "value": f"{bat.temperature_c:.1f}°C",
            "score": temp_score, "max": 10, "tip": temp_tip,
        })

    total = sum(c["score"] for c in checks)
    max_total = sum(c["max"] for c in checks)
    pct = (total / max_total) * 100 if max_total else 0

    return {"score": pct, "checks": checks, "battery": bat, "system": sys, "disk": disk}


def cmd_doctor(args=None) -> None:
    result = doctor()
    score = result["score"]
    color = health_color(score, good=85, warn=65)

    t = Table.grid(padding=(0, 1))
    t.add_column(style="bold")
    t.add_column(justify="right")
    t.add_column(justify="right", style="dim")
    t.add_column()

    for c in result["checks"]:
        sub_pct = (c["score"] / c["max"]) * 100
        sub_color = health_color(sub_pct, good=80, warn=50)
        t.add_row(
            c["name"],
            f"[{sub_color}]{c['score']}/{c['max']}[/]",
            c["value"],
            f"[dim]{c['tip']}[/]",
        )

    panel = Panel(
        t,
        title=f"[bold]Mac Doctor — Score: [{color}]{score:.0f}/100[/][/]",
        border_style=color,
    )
    console.print(panel)
