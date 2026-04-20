"""Disk usage, local Time Machine snapshots, cleanup suggestions."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import psutil
from rich.panel import Panel
from rich.table import Table

from macmanager.cache import cached
from macmanager.ui import bar, console, fmt_bytes, usage_color

CLEAN_TARGETS = [
    "~/Library/Caches",
    "~/Downloads",
    "~/.Trash",
    "~/Library/Logs",
    "~/Library/Developer/Xcode/DerivedData",
    "~/Library/Developer/CoreSimulator/Caches",
    "~/Library/Application Support/Code/Cache",
    "~/Library/Application Support/Code/CachedData",
    "~/.npm/_cacache",
    "~/Library/pnpm/store",
]


@dataclass
class DiskInfo:
    total: int
    used: int
    free: int
    percent: float
    snapshots: list[str] = field(default_factory=list)
    cleanup: list[tuple[str, int]] = field(default_factory=list)


def _du(path: str, timeout: int = 10) -> Optional[int]:
    """Size in bytes of a directory (without expanding filesystems)."""
    try:
        out = subprocess.run(
            ["du", "-sk", path],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        ).stdout.strip()
        if not out:
            return None
        kb = int(out.split()[0])
        return kb * 1024
    except Exception:
        return None


def _snapshots() -> list[str]:
    try:
        out = subprocess.run(
            ["tmutil", "listlocalsnapshots", "/"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        ).stdout
    except Exception:
        return []
    return [line.strip() for line in out.splitlines() if line.strip().startswith("com.apple")]


@cached(ttl=30)
def get_disk(scan_cleanup: bool = True) -> DiskInfo:
    du = psutil.disk_usage("/")
    info = DiskInfo(total=du.total, used=du.used, free=du.free, percent=du.percent)
    info.snapshots = _snapshots()

    if scan_cleanup:
        for target in CLEAN_TARGETS:
            path = os.path.expanduser(target)
            if not Path(path).exists():
                continue
            size = _du(path)
            if size is None or size == 0:
                continue
            info.cleanup.append((target, size))
        info.cleanup.sort(key=lambda x: x[1], reverse=True)

    return info


def render_disk_panel(info: Optional[DiskInfo] = None, full: bool = True) -> Panel:
    info = info or get_disk(scan_cleanup=full)

    t = Table.grid(padding=(0, 1))
    t.add_column(justify="right", style="dim")
    t.add_column()

    t.add_row(
        "Macintosh HD",
        f"[{usage_color(info.percent)}]{info.percent:5.1f}%[/]  {bar(info.percent)}  "
        f"[dim]{fmt_bytes(info.used)} / {fmt_bytes(info.total)}[/]",
    )
    t.add_row("Free", f"[bold]{fmt_bytes(info.free)}[/]")

    if info.snapshots:
        t.add_row("", "")
        t.add_row(
            "Local snapshots",
            f"[yellow]{len(info.snapshots)}[/] (Time Machine local) "
            f"[dim]— removed automatically under pressure[/]",
        )

    if full and info.cleanup:
        t.add_row("", "")
        t.add_row("[bold]Cleanup candidates[/]", "")
        total = 0
        for path, size in info.cleanup:
            total += size
            t.add_row(f"[dim]{path}[/]", f"{fmt_bytes(size)}")
        t.add_row("", f"[bold cyan]Total recoverable: {fmt_bytes(total)}[/]")
        t.add_row(
            "",
            "[dim]Nothing is deleted automatically. Use `mm clean --dry-run` or see suggestions with `mm clean`.[/]",
        )

    return Panel(t, title="[bold]Disk[/]", border_style="green")


def cmd_disk(args=None) -> None:
    console.print(render_disk_panel())


def cmd_clean(args=None) -> None:
    """Shows what can be cleaned (and how). For safety, deletes nothing."""
    info = get_disk(scan_cleanup=True)
    console.print(render_disk_panel(info, full=True))

    console.print("\n[bold]Suggested commands:[/]")
    console.print("[dim]# Empty the Trash:[/]")
    console.print("  rm -rf ~/.Trash/*")
    console.print("[dim]# App caches (review before!):[/]")
    console.print("  rm -rf ~/Library/Caches/*")
    if info.snapshots:
        console.print("[dim]# Delete local snapshots (Time Machine):[/]")
        for snap in info.snapshots[:3]:
            ts = snap.replace("com.apple.TimeMachine.", "").replace(".local", "")
            console.print(f"  tmutil deletelocalsnapshots {ts}")
    console.print("[dim]# Clean Xcode caches:[/]")
    console.print("  rm -rf ~/Library/Developer/Xcode/DerivedData/*")
