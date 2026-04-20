"""Battery readout via ioreg + pmset."""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass
from typing import Optional

from rich.panel import Panel
from rich.table import Table

from macmanager.cache import cached
from macmanager.ui import bar, console, fmt_seconds, health_color, usage_color


@dataclass
class BatteryInfo:
    percent: float  # 0-100
    is_charging: bool
    power_source: str  # "AC Power" | "Battery Power"
    time_remaining_sec: Optional[int]  # remaining time (discharge or until full)
    cycle_count: int
    max_capacity_mah: int
    design_capacity_mah: int
    health_percent: float  # max / design * 100
    temperature_c: Optional[float]
    fully_charged: bool
    serial: Optional[str]


_IOREG_KEYS = (
    "CycleCount",
    "AppleRawMaxCapacity",
    "DesignCapacity",
    "Temperature",
    "IsCharging",
    "FullyCharged",
    "CurrentCapacity",
    "MaxCapacity",
    "BatterySerialNumber",
    "AppleRawCurrentCapacity",
)


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout


def _parse_ioreg() -> dict:
    """Parse the top-level properties of AppleSmartBattery.

    Careful: ioreg includes a `BatteryData = { ... "DesignCapacity"=N, ... }` blob
    with subkeys of the same names. So we anchor the regex at the start of the line
    and require spaces around `=` (top-level field format)."""
    raw = _run(["ioreg", "-rn", "AppleSmartBattery"])
    data: dict = {}
    for key in _IOREG_KEYS:
        m = re.search(
            rf'^\s*"{key}"\s+=\s+(.+?)\s*$',
            raw,
            flags=re.MULTILINE,
        )
        if not m:
            continue
        val = m.group(1).strip()
        if val in ("Yes", "True"):
            data[key] = True
        elif val in ("No", "False"):
            data[key] = False
        elif val.startswith('"') and val.endswith('"'):
            data[key] = val[1:-1]
        else:
            try:
                data[key] = int(val)
            except ValueError:
                data[key] = val
    return data


_PMSET_RE = re.compile(
    r"(\d+)%;\s*([A-Za-z ]+);\s*([\d:]+)\s*remaining|"
    r"(\d+)%;\s*([A-Za-z ]+)"
)


def _parse_pmset() -> tuple[Optional[str], Optional[int]]:
    """Returns (power_source, time_remaining_sec) — pmset is usually
    more reliable for the calculated remaining time."""
    raw = _run(["pmset", "-g", "batt"])
    source = None
    first = raw.splitlines()[0] if raw else ""
    if "AC Power" in first:
        source = "AC Power"
    elif "Battery Power" in first:
        source = "Battery Power"

    time_sec: Optional[int] = None
    m = re.search(r"(\d+):(\d+)\s+remaining", raw)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        time_sec = h * 3600 + mi * 60
    return source, time_sec


@cached(ttl=2)
def get_battery() -> BatteryInfo:
    io = _parse_ioreg()
    source, time_sec = _parse_pmset()

    # CurrentCapacity in ioreg may already be in % (0-100) on Apple Silicon.
    current = io.get("CurrentCapacity")
    raw_current = io.get("AppleRawCurrentCapacity")
    raw_max = io.get("AppleRawMaxCapacity") or io.get("MaxCapacity") or 0
    design = io.get("DesignCapacity") or 0

    if isinstance(current, int) and current <= 100:
        percent = float(current)
    elif raw_current and raw_max:
        percent = (raw_current / raw_max) * 100.0
    else:
        percent = 0.0

    health = (raw_max / design) * 100.0 if raw_max and design else 0.0

    temp = io.get("Temperature")
    temp_c = (temp / 100.0) if isinstance(temp, int) else None

    return BatteryInfo(
        percent=round(percent, 1),
        is_charging=bool(io.get("IsCharging", False)),
        power_source=source or ("AC Power" if io.get("IsCharging") else "Battery Power"),
        time_remaining_sec=time_sec,
        cycle_count=int(io.get("CycleCount", 0) or 0),
        max_capacity_mah=int(raw_max or 0),
        design_capacity_mah=int(design or 0),
        health_percent=round(health, 1),
        temperature_c=round(temp_c, 1) if temp_c is not None else None,
        fully_charged=bool(io.get("FullyCharged", False)),
        serial=io.get("BatterySerialNumber"),
    )


def cycle_color(cycles: int) -> str:
    """Apple considers 1000 cycles as the lifespan for modern Macs."""
    if cycles < 300:
        return "green"
    if cycles < 700:
        return "yellow"
    return "red"


def render_battery_panel(info: Optional[BatteryInfo] = None) -> Panel:
    info = info or get_battery()

    pct_color = "green"
    if info.percent <= 20:
        pct_color = "red"
    elif info.percent <= 40:
        pct_color = "yellow"

    state = "Charging" if info.is_charging else ("Full" if info.fully_charged else "Discharging")

    t = Table.grid(padding=(0, 1))
    t.add_column(justify="right", style="dim")
    t.add_column()

    t.add_row(
        "Charge", f"[{pct_color}]{info.percent:.1f}%[/]  {bar(info.percent, color=pct_color)}"
    )
    t.add_row("State", f"{state}  · source: [bold]{info.power_source}[/]")
    if (
        info.time_remaining_sec is not None
        and info.time_remaining_sec > 0
        and not info.fully_charged
    ):
        label = "Time to full" if info.is_charging else "Time remaining"
        t.add_row(label, fmt_seconds(info.time_remaining_sec))

    t.add_row("", "")
    t.add_row(
        "Health",
        f"[{health_color(info.health_percent)}]{info.health_percent:.1f}%[/]  "
        f"({info.max_capacity_mah}/{info.design_capacity_mah} mAh)",
    )
    t.add_row("Cycles", f"[{cycle_color(info.cycle_count)}]{info.cycle_count}[/] / 1000")
    if info.temperature_c is not None:
        t.add_row(
            "Temperature",
            f"[{usage_color(info.temperature_c, warn=35, crit=40)}]{info.temperature_c:.1f}°C[/]",
        )
    if info.serial:
        t.add_row("Serial", f"[dim]{info.serial}[/]")

    return Panel(t, title="[bold]Battery[/]", border_style="cyan")


def cmd_battery(args=None) -> None:
    console.print(render_battery_panel())


def battery_dict() -> dict:
    """For logging/integrations."""
    return asdict(get_battery())
