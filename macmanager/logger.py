"""Persistence: daily CSV log to track degradation over time."""

from __future__ import annotations

import csv
import math
import os
import platform
import shutil
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from macmanager.battery import get_battery
from macmanager.ui import console

_DATA_FILES = ("battery.csv", ".alert_state")
_LEGACY_LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"


def default_logs_dir(*, home: Path | None = None, system: str | None = None) -> Path:
    """Diretório estável do usuário — sobrevive a upgrade de pipx/Homebrew.

    No Mac: ~/Library/Application Support/mac-manager
    Em outros SOs (CI Linux): ~/.local/share/mac-manager
    """
    home = home or Path.home()
    system = platform.system() if system is None else system
    if system == "Darwin":
        return home / "Library" / "Application Support" / "mac-manager"
    return home / ".local" / "share" / "mac-manager"


def resolve_logs_dir(
    *,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    system: str | None = None,
) -> Path:
    """MACMANAGER_LOGS_DIR ganha; senão o diretório padrão da plataforma."""
    environ = os.environ if env is None else env
    override = (environ.get("MACMANAGER_LOGS_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return default_logs_dir(home=home, system=system)


def migrate_legacy(legacy_dir: Path, dest_dir: Path) -> list[str]:
    """Copia CSV/estado antigos se o destino ainda não tiver o arquivo."""
    copied: list[str] = []
    if legacy_dir.resolve() == dest_dir.resolve():
        return copied
    for name in _DATA_FILES:
        src = legacy_dir / name
        dest = dest_dir / name
        if src.is_file() and not dest.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(name)
    return copied


LOGS_DIR = resolve_logs_dir()
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


def ensure_logs() -> Path:
    """Garante o diretório e migra dados do `logs/` antigo do pacote."""
    migrate_legacy(_LEGACY_LOGS_DIR, LOGS_DIR)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR


def log_battery() -> dict:
    """Appends a battery snapshot to the CSV."""
    ensure_logs()
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


def parse_history_row(row: dict) -> dict[str, str] | None:
    """Formata uma linha do CSV. None se o registro estiver quebrado.

    Linha truncada ou percent vazio não pode derrubar `mm history`.
    """
    try:
        ts = (row.get("timestamp") or "").replace("T", " ").strip()
        percent = float(row["percent"])
        health = float(row["health_percent"])
        if not ts or math.isnan(percent) or math.isnan(health):
            return None
        temp_raw = row.get("temperature_c") or ""
        return {
            "when": ts,
            "charge": f"{percent:.0f}%",
            "health": f"{health:.1f}%",
            "cycles": str(row.get("cycle_count") or "—"),
            "temp": f"{temp_raw}°C" if temp_raw else "—",
            "source": "AC" if row.get("is_charging") == "1" else "Bat",
        }
    except (TypeError, ValueError, KeyError):
        return None


def cmd_history(args=None) -> None:
    """Shows the last N entries from the CSV."""
    from rich.table import Table

    ensure_logs()
    if not BATTERY_CSV.exists():
        console.print("[yellow]No history yet. Run `mm log` or wait for launchd.[/]")
        return

    n = getattr(args, "n", 10) if args else 10
    n = max(1, int(n))
    with BATTERY_CSV.open(newline="", encoding="utf-8") as fh:
        raw_rows = list(csv.DictReader(fh))
    rows = []
    for raw in raw_rows[-n:]:
        parsed = parse_history_row(raw)
        if parsed:
            rows.append(parsed)

    t = Table(title=f"Last {len(rows)} measurements", border_style="cyan")
    t.add_column("When", style="dim")
    t.add_column("Charge", justify="right")
    t.add_column("Health", justify="right")
    t.add_column("Cycles", justify="right")
    t.add_column("Temp", justify="right")
    t.add_column("Source")

    for r in rows:
        t.add_row(r["when"], r["charge"], r["health"], r["cycles"], r["temp"], r["source"])
    console.print(t)
