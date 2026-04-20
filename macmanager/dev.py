"""Inventory and audit of development tools.

Detects languages, version managers, package managers, devops tools,
editors and common CLI utilities. Collects version, path, and (optionally)
what's outdated in ecosystems that offer that info for free (brew, npm).

Everything is detected non-invasively: we just run the `--version` (or equivalent)
of each tool. Collected in parallel for speed.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Optional

from rich.panel import Panel
from rich.table import Table

from macmanager.ui import console


@dataclass
class Tool:
    name: str
    cmd: str
    version_args: tuple[str, ...] = ("--version",)
    version_regex: str = r"(\d+\.\d+(?:\.\d+)?)"
    found: bool = False
    version: Optional[str] = None
    path: Optional[str] = None


_JDK_MISSING_HINTS = (
    "no java runtime",
    "couldn't be completed",
    "couldn’t be completed",
    "unable to locate",
    "no jvm",
)


def _probe(tool: Tool) -> Tool:
    """Tries to resolve and read the tool's version. No side effects."""
    path = shutil.which(tool.cmd)
    if not path:
        return tool
    tool.found = True
    tool.path = path
    try:
        p = subprocess.run(
            [tool.cmd, *tool.version_args],
            capture_output=True, text=True, timeout=4, check=False,
        )
        out = (p.stdout + " " + p.stderr).strip()
        out_lower = out.lower()

        if any(h in out_lower for h in _JDK_MISSING_HINTS):
            tool.version = "stub (not installed)"
            return tool

        m = re.search(tool.version_regex, out)
        if m:
            tool.version = m.group(1)
        else:
            first = out.splitlines()[0] if out else ""
            tool.version = first[:40] if first else "?"
    except Exception:
        tool.version = "?"
    return tool


def _t(name: str, cmd: str = "", **kw) -> Tool:
    return Tool(name=name, cmd=cmd or name, **kw)


GROUPS: dict[str, list[Tool]] = {
    "Languages": [
        _t("Python 3", "python3"),
        _t("Node.js", "node"),
        _t("Deno", "deno"),
        _t("Bun", "bun"),
        _t("Ruby", "ruby"),
        _t("Go", "go", version_args=("version",), version_regex=r"go(\d+\.\d+(?:\.\d+)?)"),
        _t("Rust", "rustc"),
        _t("Java", "java", version_args=("-version",)),
        _t("Kotlin", "kotlin", version_args=("-version",)),
        _t("Swift", "swift", version_args=("--version",),
           version_regex=r"Swift version (\d+\.\d+(?:\.\d+)?)"),
        _t("PHP", "php"),
        _t("Elixir", "elixir"),
        _t("Erlang", "erl", version_args=("-eval", "erlang:display(erlang:system_info(otp_release)), halt().", "-noshell"),
           version_regex=r'"?(\d+(?:\.\d+)?)'),
        _t("Lua", "lua", version_args=("-v",)),
        _t("Perl", "perl", version_args=("-v",)),
        _t("Zig", "zig", version_args=("version",)),
    ],
    "Version managers": [
        _t("nvm",   "nvm"),
        _t("fnm",   "fnm"),
        _t("volta", "volta"),
        _t("pyenv", "pyenv"),
        _t("rbenv", "rbenv"),
        _t("asdf",  "asdf"),
        _t("mise",  "mise"),
    ],
    "Package managers": [
        _t("Homebrew", "brew"),
        _t("npm",      "npm"),
        _t("pnpm",     "pnpm"),
        _t("yarn",     "yarn"),
        _t("pip",      "pip3"),
        _t("pipx",     "pipx"),
        _t("poetry",   "poetry"),
        _t("uv",       "uv"),
        _t("cargo",    "cargo"),
        _t("gem",      "gem"),
        _t("composer", "composer"),
        _t("mas",      "mas"),
    ],
    "DevOps / Infra": [
        _t("Docker",     "docker"),
        _t("Podman",     "podman"),
        _t("Colima",     "colima"),
        _t("kubectl",    "kubectl", version_args=("version", "--client", "--short"),
           version_regex=r"v?(\d+\.\d+(?:\.\d+)?)"),
        _t("Helm",       "helm"),
        _t("Terraform",  "terraform"),
        _t("Pulumi",     "pulumi"),
        _t("Ansible",    "ansible"),
        _t("AWS CLI",    "aws"),
        _t("gcloud",     "gcloud"),
        _t("Azure CLI",  "az"),
        _t("Vercel CLI", "vercel"),
        _t("Netlify CLI","netlify"),
        _t("Fly.io",     "flyctl"),
    ],
    "Git & GitHub": [
        _t("git",       "git"),
        _t("gh",        "gh"),
        _t("git-lfs",   "git-lfs"),
        _t("pre-commit","pre-commit"),
    ],
    "Editors / IDEs": [
        _t("VS Code",   "code"),
        _t("Cursor",    "cursor"),
        _t("Sublime",   "subl"),
        _t("Neovim",    "nvim"),
        _t("Vim",       "vim", version_args=("--version",)),
        _t("Emacs",     "emacs"),
        _t("Xcode CLT", "xcode-select", version_args=("-v",),
           version_regex=r"version\s+(\d+(?:\.\d+)?)"),
    ],
    "CLI utilities": [
        _t("tmux",     "tmux", version_args=("-V",)),
        _t("jq",       "jq",   version_args=("--version",), version_regex=r"jq-(\d+\.\d+)"),
        _t("ripgrep",  "rg"),
        _t("fzf",      "fzf"),
        _t("bat",      "bat"),
        _t("eza",      "eza"),
        _t("fd",       "fd"),
        _t("htop",     "htop"),
        _t("btop",     "btop"),
        _t("zoxide",   "zoxide"),
        _t("starship", "starship"),
    ],
    "Shells": [
        _t("zsh",  "zsh"),
        _t("bash", "bash"),
        _t("fish", "fish"),
    ],
}


def collect(parallel: int = 16) -> dict[str, list[Tool]]:
    """Detects versions of all tools in parallel."""
    result: dict[str, list[Tool]] = {g: [] for g in GROUPS}
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {}
        for group, tools in GROUPS.items():
            for tool in tools:
                futures[pool.submit(_probe, tool)] = group
        for fut, group in futures.items():
            result[group].append(fut.result())
    for group in result:
        result[group].sort(key=lambda t: (not t.found, t.name.lower()))
    return result


def _git_identity() -> Optional[str]:
    try:
        name = subprocess.run(
            ["git", "config", "--global", "user.name"],
            capture_output=True, text=True, timeout=2,
        ).stdout.strip()
        email = subprocess.run(
            ["git", "config", "--global", "user.email"],
            capture_output=True, text=True, timeout=2,
        ).stdout.strip()
        if name or email:
            return f"{name} <{email}>" if email else name
    except Exception:
        pass
    return None


def render_dev_panels(data: Optional[dict[str, list[Tool]]] = None,
                      show_missing: bool = False) -> list[Panel]:
    data = data or collect()
    panels: list[Panel] = []

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()

    total_found = sum(1 for tools in data.values() for t in tools if t.found)
    total = sum(len(tools) for tools in data.values())
    summary.add_row("Detected", f"[green]{total_found}[/] of {total} known tools")
    git_id = _git_identity()
    if git_id:
        summary.add_row("Git identity", git_id)

    panels.append(Panel(summary, title="[bold]Summary[/]", border_style="cyan"))

    for group, tools in data.items():
        found = [t for t in tools if t.found]
        missing = [t for t in tools if not t.found]

        if not found and not show_missing:
            continue

        t = Table.grid(padding=(0, 2))
        t.add_column(style="bold", min_width=14)
        t.add_column(style="cyan", min_width=14)
        t.add_column(style="dim")

        for tool in found:
            t.add_row(tool.name, tool.version or "?", tool.path or "")

        if show_missing and missing:
            t.add_row("", "", "")
            for tool in missing:
                t.add_row(f"[dim]{tool.name}[/]", "[dim]—[/]", "[dim](not installed)[/]")

        title = f"[bold]{group}[/]  [dim]({len(found)}/{len(tools)})[/]"
        panels.append(Panel(t, title=title, border_style="magenta"))

    return panels


def cmd_dev(args=None) -> None:
    show_missing = bool(getattr(args, "all", False))
    for panel in render_dev_panels(show_missing=show_missing):
        console.print(panel)


# ---------- subcommand: outdated check ----------

def _outdated_brew() -> list[str]:
    if not shutil.which("brew"):
        return []
    try:
        p = subprocess.run(
            ["brew", "outdated", "--quiet"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return [l for l in p.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def _outdated_npm_global() -> list[str]:
    if not shutil.which("npm"):
        return []
    try:
        p = subprocess.run(
            ["npm", "outdated", "-g", "--parseable"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        names = []
        for line in p.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 2:
                names.append(parts[1])
        return names
    except Exception:
        return []


def _outdated_pip() -> list[str]:
    if not shutil.which("pip3"):
        return []
    try:
        p = subprocess.run(
            ["pip3", "list", "--outdated", "--format=columns"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        lines = p.stdout.splitlines()[2:]
        return [l.split()[0] for l in lines if l.strip()]
    except Exception:
        return []


def _outdated_mas() -> list[str]:
    if not shutil.which("mas"):
        return []
    try:
        p = subprocess.run(
            ["mas", "outdated"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        return [l for l in p.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def cmd_dev_check(args=None) -> None:
    console.print("[dim]Checking for available updates (this can take a few seconds)...[/]\n")

    sources: list[tuple[str, Callable[[], list[str]], str]] = [
        ("Homebrew", _outdated_brew, "brew upgrade"),
        ("npm (global)", _outdated_npm_global, "npm update -g"),
        ("pip", _outdated_pip, "pip3 install -U <package>"),
        ("Mac App Store", _outdated_mas, "mas upgrade"),
    ]

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda s: (s[0], s[1](), s[2]), sources))

    total = 0
    for name, items, upgrade_cmd in results:
        if not items:
            console.print(f"[green]OK  [/] [bold]{name}[/]: up to date or unavailable")
            continue
        total += len(items)
        console.print(f"[yellow]WARN[/] [bold]{name}[/]: {len(items)} outdated")
        for it in items[:8]:
            console.print(f"      [dim]·[/] {it}")
        if len(items) > 8:
            console.print(f"      [dim]... +{len(items) - 8} more[/]")
        console.print(f"      [dim]To update:[/] {upgrade_cmd}")

    console.print()
    if total == 0:
        console.print("[green]No pending updates.[/]")
    else:
        console.print(f"[bold]{total}[/] package(s) with new version available.")
