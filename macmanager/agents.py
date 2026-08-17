"""Registro dos agents launchd (log diário + alertas de bateria).

`brew`/`pipx` instalam só o CLI. `mm setup` grava os plists em
`~/Library/LaunchAgents/` apontando para o `mm` que o usuário acabou
de invocar — caminho absoluto, sem seguir symlink, para o Cellar do
Homebrew não quebrar no próximo upgrade.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess
from xml.sax.saxutils import escape

from macmanager.logger import ensure_logs
from macmanager.ui import console, safe_text

LABEL_LOG = "com.macmanager.battery-log"
LABEL_ALERT = "com.macmanager.battery-alert"

LaunchctlRunner = Callable[[Sequence[str]], CompletedProcess[str]]


@dataclass(frozen=True)
class AgentSpec:
    label: str
    extra_args: tuple[str, ...]
    stdout_name: str
    stderr_name: str
    start_interval: int | None = None
    calendar_hour: int | None = None
    calendar_minute: int | None = None
    summary: str = ""


AGENTS: tuple[AgentSpec, ...] = (
    AgentSpec(
        label=LABEL_LOG,
        extra_args=("log",),
        stdout_name="launchd-log.out",
        stderr_name="launchd-log.err",
        calendar_hour=9,
        calendar_minute=0,
        summary="daily at 09:00 → mm log",
    ),
    AgentSpec(
        label=LABEL_ALERT,
        extra_args=("alerts",),
        stdout_name="launchd-alert.out",
        stderr_name="launchd-alert.err",
        start_interval=900,
        summary="every 15 min → mm alerts",
    ),
)


class MmBinaryNotFoundError(FileNotFoundError):
    """Não achamos um executável `mm` para colocar no plist."""


def launch_agents_dir(*, home: Path | None = None) -> Path:
    return (home or Path.home()) / "Library" / "LaunchAgents"


def _absolute(path: Path) -> Path:
    """Absoluto sem seguir symlink — `/opt/homebrew/bin/mm` precisa sobreviver ao upgrade."""
    return path.expanduser().absolute()


def resolve_mm_bin(
    *,
    argv0: str | None = None,
    executable: str | None = None,
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] | None = None,
) -> Path:
    """Caminho que o launchd deve exec. Prioridade: env, argv0, venv, PATH."""
    environ = os.environ if env is None else env
    override = (environ.get("MACMANAGER_BIN") or "").strip()
    if override:
        path = _absolute(Path(override))
        if not path.is_file():
            raise MmBinaryNotFoundError(f"MACMANAGER_BIN is not a file: {path}")
        return path

    raw = argv0 if argv0 is not None else sys.argv[0]
    candidate = _absolute(Path(raw))
    if candidate.name in {"mm", "mm.exe"} and candidate.is_file():
        return candidate

    py = Path(executable if executable is not None else sys.executable)
    sibling = _absolute(py.parent / "mm")
    if sibling.is_file():
        return sibling

    finder = shutil.which if which is None else which
    found = finder("mm")
    if found:
        return _absolute(Path(found))

    raise MmBinaryNotFoundError(
        "could not find the `mm` executable. Run `mm setup` via the installed "
        "command (not `python -m`), or set MACMANAGER_BIN to its absolute path."
    )


def _xml_string(value: str) -> str:
    return f"<string>{escape(value)}</string>"


def render_plist(*, spec: AgentSpec, mm_bin: Path, logs_dir: Path) -> str:
    """Gera o XML do LaunchAgent. Paths entram escapados (SSID não, mas `&` em path sim)."""
    args = "\n".join(f"            {_xml_string(part)}" for part in (str(mm_bin), *spec.extra_args))
    if spec.start_interval is not None:
        schedule = f"    <key>StartInterval</key>\n    <integer>{spec.start_interval}</integer>"
    else:
        hour = spec.calendar_hour if spec.calendar_hour is not None else 9
        minute = spec.calendar_minute if spec.calendar_minute is not None else 0
        schedule = (
            "    <key>StartCalendarInterval</key>\n"
            "    <dict>\n"
            "        <key>Hour</key>\n"
            f"        <integer>{hour}</integer>\n"
            "        <key>Minute</key>\n"
            f"        <integer>{minute}</integer>\n"
            "    </dict>"
        )
    stdout = _xml_string(str(logs_dir / spec.stdout_name))
    stderr = _xml_string(str(logs_dir / spec.stderr_name))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"\n'
        '  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        "    <key>Label</key>\n"
        f"    {_xml_string(spec.label)}\n"
        "\n"
        "    <key>ProgramArguments</key>\n"
        "    <array>\n"
        f"{args}\n"
        "    </array>\n"
        "\n"
        f"{schedule}\n"
        "\n"
        "    <key>RunAtLoad</key>\n"
        "    <true/>\n"
        "\n"
        "    <key>StandardOutPath</key>\n"
        f"    {stdout}\n"
        "    <key>StandardErrorPath</key>\n"
        f"    {stderr}\n"
        "</dict>\n"
        "</plist>\n"
    )


def _default_launchctl(args: Sequence[str]) -> CompletedProcess[str]:
    return subprocess.run(list(args), capture_output=True, text=True, check=False)


def _gui_target(uid: int, label: str) -> str:
    return f"gui/{uid}/{label}"


def unload_agent(
    spec: AgentSpec,
    plist: Path,
    *,
    uid: int,
    runner: LaunchctlRunner,
) -> None:
    """Tira o agent do launchd. bootout primeiro; unload se o macOS for antigo."""
    bootout = runner(["launchctl", "bootout", _gui_target(uid, spec.label)])
    if bootout.returncode != 0 and plist.is_file():
        runner(["launchctl", "unload", str(plist)])


def load_agent(
    spec: AgentSpec,
    plist: Path,
    *,
    uid: int,
    runner: LaunchctlRunner,
) -> CompletedProcess[str]:
    loaded = runner(["launchctl", "bootstrap", f"gui/{uid}", str(plist)])
    if loaded.returncode == 0:
        return loaded
    return runner(["launchctl", "load", str(plist)])


def install_agents(
    *,
    mm_bin: Path,
    agents_dir: Path,
    logs_dir: Path,
    uid: int,
    runner: LaunchctlRunner,
    darwin: bool,
) -> list[tuple[AgentSpec, Path, bool]]:
    """Escreve os plists e, no Mac, (re)carrega no launchd.

    Retorna (spec, path, loaded). `loaded` é True se o launchctl aceitou
    ou se pulamos o launchctl (`darwin=False`, nos testes).
    """
    agents_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[AgentSpec, Path, bool]] = []
    for spec in AGENTS:
        dest = agents_dir / f"{spec.label}.plist"
        dest.write_text(render_plist(spec=spec, mm_bin=mm_bin, logs_dir=logs_dir), encoding="utf-8")
        loaded = True
        if darwin:
            unload_agent(spec, dest, uid=uid, runner=runner)
            loaded = load_agent(spec, dest, uid=uid, runner=runner).returncode == 0
        results.append((spec, dest, loaded))
    return results


def remove_agents(
    *,
    agents_dir: Path,
    uid: int,
    runner: LaunchctlRunner,
    darwin: bool,
) -> list[str]:
    """Descarrega e apaga os plists. Devolve os labels que existiam no disco."""
    removed: list[str] = []
    for spec in AGENTS:
        dest = agents_dir / f"{spec.label}.plist"
        if not dest.is_file():
            continue
        if darwin:
            unload_agent(spec, dest, uid=uid, runner=runner)
        dest.unlink()
        removed.append(spec.label)
    return removed


def cmd_setup(args=None) -> int:
    """Registra os agents. Só faz sentido no macOS."""
    system = platform.system()
    if system != "Darwin":
        console.print("[red]mm setup[/] is only available on macOS (launchd).")
        return 1

    try:
        mm_bin = resolve_mm_bin()
    except MmBinaryNotFoundError as exc:
        console.print(f"[red]{safe_text(exc)}[/]")
        return 1

    logs_dir = ensure_logs()
    results = install_agents(
        mm_bin=mm_bin,
        agents_dir=launch_agents_dir(),
        logs_dir=logs_dir,
        uid=os.getuid(),
        runner=_default_launchctl,
        darwin=True,
    )

    console.print("[bold]Registered launchd agents[/]")
    failed = False
    for spec, dest, loaded in results:
        mark = "[green]ok[/]" if loaded else "[red]launchctl failed[/]"
        if not loaded:
            failed = True
        console.print(f"  {mark}  {spec.label}  ({spec.summary})")
        console.print(f"         {safe_text(dest)}")
    console.print()
    console.print(f"Binary: {safe_text(mm_bin)}")
    console.print(f"Logs:   {safe_text(logs_dir)}")
    console.print()
    console.print("Daily log at 09:00 and battery alerts every 15 min.")
    console.print("To stop them later: [bold]mm uninstall[/]")
    return 1 if failed else 0


def cmd_uninstall(args=None) -> int:
    """Remove só os agents. brew/pipx/venv ficam — isso não é `brew uninstall`."""
    darwin = platform.system() == "Darwin"
    removed = remove_agents(
        agents_dir=launch_agents_dir(),
        uid=os.getuid(),
        runner=_default_launchctl,
        darwin=darwin,
    )
    if not removed:
        console.print("No Mac Manager launchd agents were installed.")
        return 0

    console.print("[bold]Removed launchd agents[/]")
    for label in removed:
        console.print(f"  • {label}")
    console.print()
    console.print("Battery history in ~/Library/Application Support/mac-manager/ was preserved.")
    console.print()
    console.print("To remove the CLI itself:")
    console.print("  brew uninstall mac-manager")
    console.print("  # or: pipx uninstall mac-manager")
    return 0
