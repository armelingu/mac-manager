"""macOS security audit.

Sequentially checks: FileVault, Firewall, SIP, Gatekeeper, system updates,
auto-updates, antimalware (XProtect), time since last reboot, and login items.
Each check becomes a row with status OK/WARN/FAIL and yields a 0-100 score at the end.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from rich.panel import Panel
from rich.table import Table

from macmanager.cache import cached
from macmanager.ui import console, fmt_seconds, health_color


OK, WARN, FAIL, INFO = "OK", "WARN", "FAIL", "INFO"

STATUS_STYLE = {
    OK:   "[green]OK  [/]",
    WARN: "[yellow]WARN[/]",
    FAIL: "[red]FAIL[/]",
    INFO: "[dim]INFO[/]",
}

STATUS_SCORE = {OK: 1.0, INFO: 1.0, WARN: 0.4, FAIL: 0.0}


@dataclass
class Check:
    name: str
    status: str
    detail: str
    weight: int = 1
    tip: str = ""


def _run(cmd: list[str], timeout: int = 5) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return -1, "", ""


def check_filevault() -> Check:
    rc, out, _ = _run(["fdesetup", "status"])
    if rc != 0:
        return Check("FileVault", WARN, "could not query", 3,
                    "Run `sudo fdesetup status` for details.")
    if "FileVault is On" in out:
        return Check("FileVault", OK, "active", 3)
    return Check("FileVault", FAIL, "DISABLED", 3,
                "Enable in Settings > Privacy & Security > FileVault.")


def check_firewall() -> Check:
    """On macOS Sequoia `defaults` requires permission; we try `socketfilterfw`."""
    sff = "/usr/libexec/ApplicationFirewall/socketfilterfw"
    if Path(sff).exists():
        rc, out, _ = _run([sff, "--getglobalstate"])
        if rc == 0 and out:
            text = out.lower()
            if "enabled" in text:
                return Check("Firewall", OK, "active", 2)
            if "disabled" in text:
                return Check("Firewall", FAIL, "disabled", 2,
                            "Enable in Settings > Network > Firewall.")

    rc, out, _ = _run(["defaults", "read",
                       "/Library/Preferences/com.apple.alf", "globalstate"])
    if rc != 0:
        return Check("Firewall", WARN, "requires permission; check in Settings > Network > Firewall", 2)
    state = out.strip()
    if state == "0":
        return Check("Firewall", FAIL, "disabled", 2,
                    "Enable in Settings > Network > Firewall.")
    if state in ("1", "2"):
        suffix = " (signed connections only)" if state == "2" else ""
        return Check("Firewall", OK, f"active{suffix}", 2)
    return Check("Firewall", WARN, f"unknown state ({state})", 2)


def check_sip() -> Check:
    rc, out, _ = _run(["csrutil", "status"])
    if rc != 0:
        return Check("SIP", WARN, "could not query", 3)
    if "enabled" in out.lower():
        return Check("SIP", OK, "active (System Integrity Protection)", 3)
    return Check("SIP", FAIL, "DISABLED", 3,
                "Re-enable in recovery mode: `csrutil enable`.")


def check_gatekeeper() -> Check:
    rc, out, _ = _run(["spctl", "--status"])
    if rc != 0:
        return Check("Gatekeeper", WARN, "could not query", 2)
    if "assessments enabled" in out:
        return Check("Gatekeeper", OK, "active", 2)
    return Check("Gatekeeper", FAIL, "DISABLED", 2,
                "Re-enable with `sudo spctl --master-enable`.")


def check_macos_version() -> Check:
    rc, out, _ = _run(["sw_vers"])
    if rc != 0:
        return Check("macOS version", WARN, "—", 1)
    name = re.search(r"ProductName:\s*(.+)", out)
    ver = re.search(r"ProductVersion:\s*(.+)", out)
    build = re.search(r"BuildVersion:\s*(.+)", out)
    label = " ".join(filter(None, [
        name.group(1).strip() if name else "",
        ver.group(1).strip() if ver else "",
        f"({build.group(1).strip()})" if build else "",
    ]))
    return Check("macOS version", INFO, label, 0)


@cached(ttl=900)
def check_macos_updates() -> Check:
    rc, out, err = _run(["softwareupdate", "--list"], timeout=20)
    text = (out + "\n" + err).lower()
    if rc != 0:
        return Check("Pending updates", WARN, "could not query", 2)
    if "no new software available" in text:
        return Check("Pending updates", OK, "none", 2)

    items: list[str] = []
    for line in out.splitlines():
        m = re.search(r"Title:\s*([^,]+),\s*Version:\s*([^,]+)", line)
        if m:
            items.append(f"{m.group(1).strip()} {m.group(2).strip()}")
    if not items:
        for line in out.splitlines():
            m = re.match(r"\s*\*\s*Label:\s*(.+?)\s*$", line, re.IGNORECASE)
            if m:
                items.append(m.group(1))

    if items:
        first = items[0]
        more = f" (+{len(items) - 1} more)" if len(items) > 1 else ""
        return Check("Pending updates", WARN,
                     f"{len(items)} pending: {first}{more}", 2,
                     "Update in Settings > General > Software Update.")
    return Check("Pending updates", OK, "none detected", 2)


def check_auto_updates() -> Check:
    """May require permission; we try `softwareupdate --schedule` as fallback."""
    rc, out, _ = _run(["defaults", "read",
                       "/Library/Preferences/com.apple.SoftwareUpdate",
                       "AutomaticCheckEnabled"])
    if rc == 0 and out.strip() in ("0", "1"):
        if out.strip() == "1":
            return Check("Automatic check", OK, "enabled", 1)
        return Check("Automatic check", WARN, "disabled", 1,
                    "Enable in Settings > General > Software Update.")

    rc, out, _ = _run(["softwareupdate", "--schedule"])
    if rc == 0 and out:
        text = out.lower()
        if "is on" in text or "automatic check is on" in text:
            return Check("Automatic check", OK, "enabled", 1)
        if "is off" in text:
            return Check("Automatic check", WARN, "disabled", 1,
                        "Enable in Settings > General > Software Update.")

    return Check("Automatic check", WARN, "requires permission; check in Settings", 1)


def check_xprotect() -> Check:
    info_paths = [
        "/Library/Apple/System/Library/CoreServices/XProtect.bundle/Contents/Info.plist",
        "/System/Library/CoreServices/XProtect.bundle/Contents/Info.plist",
    ]
    for path in info_paths:
        if not Path(path).exists():
            continue
        rc, out, _ = _run(["defaults", "read", path[:-6], "CFBundleShortVersionString"])
        if rc == 0 and out.strip():
            return Check("XProtect (antimalware)", INFO, f"version {out.strip()}", 0)
    return Check("XProtect (antimalware)", INFO, "—", 0)


def check_uptime() -> Check:
    rc, out, _ = _run(["sysctl", "-n", "kern.boottime"])
    if rc != 0:
        return Check("Time since last reboot", WARN, "—", 1)
    m = re.search(r"sec\s*=\s*(\d+)", out)
    if not m:
        return Check("Time since last reboot", WARN, "—", 1)
    import time
    boot = int(m.group(1))
    up = int(time.time() - boot)
    days = up / 86400
    label = fmt_seconds(up)
    if days < 7:
        return Check("Time since last reboot", OK, label, 1)
    if days < 21:
        return Check("Time since last reboot", WARN, label, 1,
                    "Reboot to apply pending kernel updates.")
    return Check("Time since last reboot", FAIL, label, 1,
                "More than 3 weeks without rebooting — risk of unapplied updates.")


def check_login_items() -> Check:
    """Counts agents that load on the user's login."""
    paths = [
        Path.home() / "Library/LaunchAgents",
        Path("/Library/LaunchAgents"),
    ]
    items: list[str] = []
    for p in paths:
        if p.exists():
            items.extend(sorted(f.stem for f in p.glob("*.plist")))

    n = len(items)
    if n == 0:
        return Check("LaunchAgents (login)", OK, "none", 1)
    label = f"{n} agent(s)"
    if n <= 10:
        status = OK
    elif n <= 25:
        status = WARN
    else:
        status = WARN
    return Check("LaunchAgents (login)", status, label, 1,
                "List with `ls ~/Library/LaunchAgents /Library/LaunchAgents`.")


def check_remote_login() -> Check:
    """Remote SSH should be off for regular users."""
    rc, out, _ = _run(["systemsetup", "-getremotelogin"], timeout=3)
    if rc != 0:
        return Check("Remote SSH", INFO, "—", 0)
    if "On" in out:
        return Check("Remote SSH", WARN, "enabled", 1,
                    "Disable if you don't use it: `sudo systemsetup -setremotelogin off`.")
    return Check("Remote SSH", OK, "disabled", 1)


CHECKS = [
    check_macos_version,
    check_filevault,
    check_sip,
    check_gatekeeper,
    check_firewall,
    check_macos_updates,
    check_auto_updates,
    check_xprotect,
    check_uptime,
    check_remote_login,
    check_login_items,
]


@cached(ttl=300)
def run_all() -> list[Check]:
    return [fn() for fn in CHECKS]


def render_security_panel(checks: Optional[list[Check]] = None) -> Panel:
    checks = checks or run_all()

    weighted_total = sum(c.weight for c in checks if c.weight > 0)
    weighted_score = sum(STATUS_SCORE.get(c.status, 0) * c.weight
                         for c in checks if c.weight > 0)
    score = (weighted_score / weighted_total) * 100 if weighted_total else 0
    color = health_color(score, good=85, warn=65)

    t = Table.grid(padding=(0, 1))
    t.add_column(width=6)
    t.add_column(style="bold", min_width=22)
    t.add_column()

    for c in checks:
        line = c.detail
        if c.tip:
            line += f"  [dim]· {c.tip}[/]"
        t.add_row(STATUS_STYLE.get(c.status, c.status), c.name, line)

    return Panel(
        t,
        title=f"[bold]Security — Score: [{color}]{score:.0f}/100[/][/]",
        border_style=color,
    )


def cmd_security(args=None) -> None:
    console.print(render_security_panel())
