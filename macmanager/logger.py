"""Persistence: daily CSV log to track degradation over time."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from macmanager.battery import get_battery
from macmanager.system import get_system
from macmanager.ui import console


LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
BATTERY_CSV = LOGS_DIR / "battery.csv"
ALERT_STATE = LOGS_DIR / ".alert_state"

BATTERY_FIELDS = [
    "timestamp",
    "percent",
    "is_charging",
    "power_source",
    "cycle_count",
    "max_capacity_mah",
    "design_capacity_mah",
    "health_percent",
    "temperature_c",
]


def _ensure_dir() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def log_battery() -> dict:
    """Appends a battery snapshot to the CSV."""
    _ensure_dir()
    info = get_battery()
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "percent": info.percent,
        "is_charging": int(info.is_charging),
        "power_source": info.power_source,
        "cycle_count": info.cycle_count,
        "max_capacity_mah": info.max_capacity_mah,
        "design_capacity_mah": info.design_capacity_mah,
        "health_percent": info.health_percent,
        "temperature_c": info.temperature_c if info.temperature_c is not None else "",
    }

    new_file = not BATTERY_CSV.exists()
    with BATTERY_CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BATTERY_FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(row)
    return row


def cmd_log(args=None) -> None:
    row = log_battery()
    console.print(f"[green]OK[/] Log written to [dim]{BATTERY_CSV}[/]")
    console.print(
        f"  charge: [bold]{row['percent']}%[/]  · health: [bold]{row['health_percent']}%[/]  "
        f"· cycles: [bold]{row['cycle_count']}[/]"
    )


def cmd_history(args=None) -> None:
    """Shows the last N entries from the CSV."""
    from rich.table import Table
    if not BATTERY_CSV.exists():
        console.print("[yellow]No history yet. Run `mm log` or wait for launchd.[/]")
        return

    n = getattr(args, "n", 10) if args else 10
    rows = list(csv.DictReader(BATTERY_CSV.open()))
    rows = rows[-n:]

    t = Table(title=f"Last {len(rows)} measurements", border_style="cyan")
    t.add_column("When", style="dim")
    t.add_column("Charge", justify="right")
    t.add_column("Health", justify="right")
    t.add_column("Cycles", justify="right")
    t.add_column("Temp", justify="right")
    t.add_column("Source")

    for r in rows:
        t.add_row(
            r["timestamp"].replace("T", " "),
            f"{float(r['percent']):.0f}%",
            f"{float(r['health_percent']):.1f}%",
            r["cycle_count"],
            f"{r['temperature_c']}°C" if r["temperature_c"] else "—",
            "AC" if r["is_charging"] == "1" else "Bat",
        )
    console.print(t)
