"""UI helpers: shared rich console, formatters."""

from __future__ import annotations

from collections.abc import Callable

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

console = Console()


def safe_panel(
    title: str,
    render: Callable[[], Panel],
    border_style: str = "red",
) -> Panel:
    """Roda o renderer e, se ele explodir, devolve um painel de fallback.

    Assim um coletor morto (timeout, MarkupError, psutil) não derruba o
    `mm` status nem o `mm watch` inteiro. `KeyboardInterrupt` e
    `SystemExit` passam — são `BaseException`, não `Exception`.
    """
    try:
        return render()
    except Exception:
        return Panel(
            "[dim]Não foi possível coletar estes dados.[/]",
            title=f"[bold]{title}[/]",
            border_style=border_style,
        )


def safe_text(value: object) -> str:
    """Escapa markup Rich em texto que veio do sistema (SSID, processo, path).

    Sem isso, um SSID `My[/Home]WiFi` ou um processo `foo[/]bar` vira
    `MarkupError` e derruba o painel.
    """
    if value is None:
        return ""
    return escape(str(value))


def fmt_bytes(num: float) -> str:
    """Format bytes in KB/MB/GB/TB in a readable way."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def fmt_seconds(secs: int | float) -> str:
    """Seconds -> "1h 23m" / "45m" / "30s"."""
    if secs is None or secs < 0:
        return "—"
    secs = int(secs)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def health_color(pct: float, good: float = 80, warn: float = 60) -> str:
    """Color based on a percentage (higher = better)."""
    if pct >= good:
        return "green"
    if pct >= warn:
        return "yellow"
    return "red"


def usage_color(pct: float, warn: float = 70, crit: float = 90) -> str:
    """Color based on usage (lower = better)."""
    if pct < warn:
        return "green"
    if pct < crit:
        return "yellow"
    return "red"


def bar(pct: float, width: int = 20, color: str | None = None) -> str:
    """Simple text-based progress bar using rich markup."""
    pct = max(0.0, min(100.0, pct))
    filled = round(width * pct / 100)
    color = color or usage_color(pct)
    return f"[{color}]{'█' * filled}{'░' * (width - filled)}[/]"
