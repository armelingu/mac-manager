"""Network info: Wi-Fi, IPs, signal quality."""

from __future__ import annotations

import contextlib
import re
import subprocess
import urllib.request
from dataclasses import dataclass
from typing import Optional

from rich.panel import Panel
from rich.table import Table

from macmanager.cache import cached
from macmanager.ui import console, safe_text


@dataclass
class NetworkInfo:
    interface: str
    local_ip: Optional[str]
    public_ip: Optional[str]
    ssid: Optional[str]
    bssid: Optional[str]
    rssi: Optional[int]  # dBm (negative)
    noise: Optional[int]
    channel: Optional[str]
    tx_rate: Optional[str]  # Mbps
    security: Optional[str]


def _run(cmd: list[str], timeout: int = 5) -> str:
    """Devolve o stdout. Timeout, binário ausente e erro de OS viram "".

    Quem chama degrada para "desconhecido" em vez de derrubar `mm` /
    `mm net` / `mm watch`. Espelha `macmanager.security._run`.
    """
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        return p.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def _local_ip(iface: str = "en0") -> Optional[str]:
    out = _run(["ipconfig", "getifaddr", iface], timeout=2).strip()
    return out or None


def parse_route_interface(raw: str) -> Optional[str]:
    """Extrai a interface da rota default (`route -n get default`)."""
    m = re.search(r"^\s*interface:\s+(\S+)", raw, flags=re.MULTILINE)
    return m.group(1) if m else None


def _active_interface() -> str:
    """Interface da rota default. Sem rota, cai em en0."""
    parsed = parse_route_interface(_run(["route", "-n", "get", "default"], timeout=2))
    return parsed or "en0"


@cached(ttl=300, cache_none=False)
def _public_ip() -> Optional[str]:
    """IP público muda pouco — cache de 5 min. None não é cacheado."""
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=2) as r:
            return r.read().decode().strip()
    except Exception:
        return None


@cached(ttl=30)
def _wifi_info() -> dict:
    """On macOS Sonoma+ `airport -I` is deprecated. We try `wdutil info`
    first (needs sudo for full details) and fall back to `system_profiler SPAirPortDataType`
    (no sudo)."""
    data: dict = {}

    out = _run(["/usr/sbin/system_profiler", "SPAirPortDataType"], timeout=5)

    cur = re.search(r"Current Network Information:\s*\n\s*([^\n]+):", out)
    if cur:
        data["ssid"] = cur.group(1).strip()

    block = re.search(
        r"Current Network Information:.*?(?=\n\s{6}\w|\Z)",
        out,
        re.DOTALL,
    )
    if block:
        b = block.group(0)
        for key, label in (
            ("bssid", r"BSSID:\s*([^\n]+)"),
            ("channel", r"Channel:\s*([^\n]+)"),
            ("security", r"Security:\s*([^\n]+)"),
            ("rssi", r"Signal / Noise:\s*(-?\d+)\s*dBm"),
            ("noise", r"Signal / Noise:.*?/\s*(-?\d+)\s*dBm"),
            ("tx_rate", r"Transmit Rate:\s*([^\n]+)"),
        ):
            m = re.search(label, b)
            if m:
                val = m.group(1).strip()
                if key in ("rssi", "noise"):
                    with contextlib.suppress(ValueError):
                        data[key] = int(val)
                else:
                    data[key] = val

    return data


@cached(ttl=10)
def get_network() -> NetworkInfo:
    iface = _active_interface()
    local = _local_ip(iface)
    public = _public_ip()
    wifi = _wifi_info()

    return NetworkInfo(
        interface=iface,
        local_ip=local,
        public_ip=public,
        ssid=wifi.get("ssid"),
        bssid=wifi.get("bssid"),
        rssi=wifi.get("rssi"),
        noise=wifi.get("noise"),
        channel=wifi.get("channel"),
        tx_rate=wifi.get("tx_rate"),
        security=wifi.get("security"),
    )


def _signal_quality(rssi: Optional[int]) -> tuple[str, str]:
    if rssi is None:
        return ("—", "dim")
    if rssi >= -55:
        return ("Excellent", "green")
    if rssi >= -67:
        return ("Good", "green")
    if rssi >= -75:
        return ("Fair", "yellow")
    return ("Weak", "red")


def render_network_panel(info: Optional[NetworkInfo] = None) -> Panel:
    info = info or get_network()

    t = Table.grid(padding=(0, 1))
    t.add_column(justify="right", style="dim")
    t.add_column()

    t.add_row("Interface", safe_text(info.interface))
    t.add_row("Local IP", safe_text(info.local_ip) or "[dim]—[/]")
    t.add_row("Public IP", safe_text(info.public_ip) or "[dim]offline[/]")
    if info.ssid:
        t.add_row("", "")
        t.add_row("Wi-Fi", f"[bold]{safe_text(info.ssid)}[/]")
        if info.security:
            t.add_row("Security", safe_text(info.security))
        if info.channel:
            t.add_row("Channel", safe_text(info.channel))
        if info.tx_rate:
            t.add_row("TX Rate", f"{safe_text(info.tx_rate)} Mbps")
        if info.rssi is not None:
            label, color = _signal_quality(info.rssi)
            t.add_row("Signal", f"[{color}]{info.rssi} dBm · {label}[/]")

    return Panel(t, title="[bold]Network[/]", border_style="blue")


def cmd_net(args=None) -> None:
    console.print(render_network_panel())
