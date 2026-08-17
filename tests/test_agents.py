"""Contract tests for `macmanager.agents`.

Não chamamos launchctl de verdade — o CI roda em Linux. O contrato é:
plist válido, path do `mm` sem seguir symlink, setup/uninstall idempotentes.
"""

from __future__ import annotations

from collections.abc import Sequence
from io import StringIO
from pathlib import Path
from subprocess import CompletedProcess

import pytest
from rich.console import Console

from macmanager.agents import (
    AGENTS,
    LABEL_ALERT,
    LABEL_LOG,
    MmBinaryNotFoundError,
    cmd_setup,
    cmd_uninstall,
    install_agents,
    launch_agents_dir,
    remove_agents,
    render_plist,
    resolve_mm_bin,
)
from macmanager.cli import build_parser


def _touch_mm(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\necho mm\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _ok(args: Sequence[str]) -> CompletedProcess[str]:
    return CompletedProcess(list(args), 0, "", "")


def _fail(args: Sequence[str]) -> CompletedProcess[str]:
    return CompletedProcess(list(args), 1, "", "failed")


class TestLaunchAgentsDir:
    def test_under_library(self, tmp_path: Path) -> None:
        assert launch_agents_dir(home=tmp_path) == tmp_path / "Library" / "LaunchAgents"


class TestResolveMmBin:
    def test_env_override_wins(self, tmp_path: Path) -> None:
        mm = _touch_mm(tmp_path / "custom" / "mm")
        resolved = resolve_mm_bin(
            argv0=str(tmp_path / "other" / "mm"),
            env={"MACMANAGER_BIN": str(mm)},
            which=lambda _name: None,
        )
        assert resolved == mm

    def test_env_override_must_exist(self, tmp_path: Path) -> None:
        with pytest.raises(MmBinaryNotFoundError, match="MACMANAGER_BIN"):
            resolve_mm_bin(
                env={"MACMANAGER_BIN": str(tmp_path / "missing")},
                which=lambda _name: None,
            )

    def test_argv0_named_mm(self, tmp_path: Path) -> None:
        mm = _touch_mm(tmp_path / "bin" / "mm")
        resolved = resolve_mm_bin(argv0=str(mm), env={}, which=lambda _name: None)
        assert resolved == mm

    def test_does_not_follow_homebrew_symlink(self, tmp_path: Path) -> None:
        cellar = _touch_mm(tmp_path / "Cellar" / "mac-manager" / "0.1.2" / "libexec" / "bin" / "mm")
        shim = tmp_path / "opt" / "homebrew" / "bin" / "mm"
        shim.parent.mkdir(parents=True)
        shim.symlink_to(cellar)
        resolved = resolve_mm_bin(argv0=str(shim), env={}, which=lambda _name: None)
        assert resolved == shim
        assert resolved.resolve() == cellar

    def test_venv_sibling_of_python(self, tmp_path: Path) -> None:
        python = _touch_mm(tmp_path / "venv" / "bin" / "python")
        mm = _touch_mm(tmp_path / "venv" / "bin" / "mm")
        resolved = resolve_mm_bin(
            argv0=str(tmp_path / "macmanager" / "cli.py"),
            executable=str(python),
            env={},
            which=lambda _name: None,
        )
        assert resolved == mm

    def test_which_fallback(self, tmp_path: Path) -> None:
        mm = _touch_mm(tmp_path / "path" / "mm")
        resolved = resolve_mm_bin(
            argv0=str(tmp_path / "cli.py"),
            executable=str(tmp_path / "python3"),
            env={},
            which=lambda name: str(mm) if name == "mm" else None,
        )
        assert resolved == mm

    def test_raises_when_nothing_found(self, tmp_path: Path) -> None:
        with pytest.raises(MmBinaryNotFoundError, match="could not find"):
            resolve_mm_bin(
                argv0=str(tmp_path / "cli.py"),
                executable=str(tmp_path / "python3"),
                env={},
                which=lambda _name: None,
            )


class TestRenderPlist:
    def test_log_agent_uses_calendar_interval(self, tmp_path: Path) -> None:
        spec = AGENTS[0]
        xml = render_plist(spec=spec, mm_bin=tmp_path / "mm", logs_dir=tmp_path / "logs")
        assert spec.label in xml
        assert "<string>log</string>" in xml
        assert "<key>StartCalendarInterval</key>" in xml
        assert "<integer>9</integer>" in xml
        assert "<integer>0</integer>" in xml
        assert "StartInterval" not in xml
        assert str(tmp_path / "logs" / "launchd-log.out") in xml

    def test_alert_agent_uses_start_interval(self, tmp_path: Path) -> None:
        spec = AGENTS[1]
        xml = render_plist(spec=spec, mm_bin=tmp_path / "mm", logs_dir=tmp_path / "logs")
        assert spec.label in xml
        assert "<string>alerts</string>" in xml
        assert "<key>StartInterval</key>" in xml
        assert "<integer>900</integer>" in xml
        assert "StartCalendarInterval" not in xml

    def test_escapes_xml_in_paths(self, tmp_path: Path) -> None:
        mm = tmp_path / "a&b" / "mm"
        logs = tmp_path / "logs<x>"
        xml = render_plist(spec=AGENTS[0], mm_bin=mm, logs_dir=logs)
        assert "a&amp;b" in xml
        assert "logs&lt;x&gt;" in xml
        assert "a&b" not in xml


class TestInstallAndRemove:
    def test_writes_both_plists_without_launchctl(self, tmp_path: Path) -> None:
        calls: list[list[str]] = []

        def runner(args: Sequence[str]) -> CompletedProcess[str]:
            calls.append(list(args))
            return _ok(args)

        mm = tmp_path / "mm"
        agents_dir = tmp_path / "LaunchAgents"
        logs_dir = tmp_path / "logs"
        results = install_agents(
            mm_bin=mm,
            agents_dir=agents_dir,
            logs_dir=logs_dir,
            uid=501,
            runner=runner,
            darwin=False,
        )
        assert calls == []
        assert {spec.label for spec, _path, loaded in results} == {LABEL_LOG, LABEL_ALERT}
        assert all(loaded for _spec, _path, loaded in results)
        log_plist = (agents_dir / f"{LABEL_LOG}.plist").read_text(encoding="utf-8")
        assert str(mm) in log_plist
        assert logs_dir.is_dir()

    def test_reloads_via_bootout_then_bootstrap(self, tmp_path: Path) -> None:
        calls: list[list[str]] = []

        def runner(args: Sequence[str]) -> CompletedProcess[str]:
            calls.append(list(args))
            return _ok(args)

        install_agents(
            mm_bin=tmp_path / "mm",
            agents_dir=tmp_path / "LaunchAgents",
            logs_dir=tmp_path / "logs",
            uid=501,
            runner=runner,
            darwin=True,
        )
        labels = [c[2] for c in calls if c[:2] == ["launchctl", "bootout"]]
        assert f"gui/501/{LABEL_LOG}" in labels
        assert f"gui/501/{LABEL_ALERT}" in labels
        bootstraps = [c for c in calls if c[:2] == ["launchctl", "bootstrap"]]
        assert len(bootstraps) == 2
        assert all(c[2] == "gui/501" for c in bootstraps)

    def test_falls_back_to_load_when_bootstrap_fails(self, tmp_path: Path) -> None:
        def runner(args: Sequence[str]) -> CompletedProcess[str]:
            if "bootstrap" in args or "bootout" in args:
                return _fail(args)
            return _ok(args)

        results = install_agents(
            mm_bin=tmp_path / "mm",
            agents_dir=tmp_path / "LaunchAgents",
            logs_dir=tmp_path / "logs",
            uid=501,
            runner=runner,
            darwin=True,
        )
        assert all(loaded for _spec, _path, loaded in results)

    def test_remove_deletes_plists(self, tmp_path: Path) -> None:
        agents_dir = tmp_path / "LaunchAgents"
        install_agents(
            mm_bin=tmp_path / "mm",
            agents_dir=agents_dir,
            logs_dir=tmp_path / "logs",
            uid=501,
            runner=_ok,
            darwin=False,
        )
        removed = remove_agents(agents_dir=agents_dir, uid=501, runner=_ok, darwin=False)
        assert removed == [LABEL_LOG, LABEL_ALERT]
        assert list(agents_dir.glob("*.plist")) == []

    def test_remove_is_idempotent_when_missing(self, tmp_path: Path) -> None:
        removed = remove_agents(
            agents_dir=tmp_path / "LaunchAgents",
            uid=501,
            runner=_ok,
            darwin=False,
        )
        assert removed == []


class TestCmdSetup:
    def test_refuses_non_darwin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("macmanager.agents.platform.system", lambda: "Linux")
        buf = StringIO()
        monkeypatch.setattr(
            "macmanager.agents.console",
            Console(file=buf, force_terminal=True, width=80),
        )
        assert cmd_setup() == 1
        assert "only available on macOS" in buf.getvalue()

    def test_registers_on_darwin(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mm = _touch_mm(tmp_path / "mm")
        agents_dir = tmp_path / "LaunchAgents"
        logs_dir = tmp_path / "logs"
        monkeypatch.setattr("macmanager.agents.platform.system", lambda: "Darwin")
        monkeypatch.setattr("macmanager.agents.resolve_mm_bin", lambda: mm)
        monkeypatch.setattr("macmanager.agents.ensure_logs", lambda: logs_dir)
        monkeypatch.setattr("macmanager.agents.launch_agents_dir", lambda: agents_dir)
        monkeypatch.setattr("macmanager.agents.os.getuid", lambda: 501)
        monkeypatch.setattr("macmanager.agents._default_launchctl", _ok)
        buf = StringIO()
        monkeypatch.setattr(
            "macmanager.agents.console",
            Console(file=buf, force_terminal=True, width=80),
        )
        assert cmd_setup() == 0
        out = buf.getvalue()
        assert LABEL_LOG in out
        assert LABEL_ALERT in out
        assert (agents_dir / f"{LABEL_LOG}.plist").is_file()


class TestCmdUninstall:
    def test_reports_when_nothing_installed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("macmanager.agents.platform.system", lambda: "Linux")
        monkeypatch.setattr(
            "macmanager.agents.launch_agents_dir", lambda: tmp_path / "LaunchAgents"
        )
        buf = StringIO()
        monkeypatch.setattr(
            "macmanager.agents.console",
            Console(file=buf, force_terminal=True, width=80),
        )
        assert cmd_uninstall() == 0
        assert "No Mac Manager launchd agents" in buf.getvalue()

    def test_removes_agents(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        agents_dir = tmp_path / "LaunchAgents"
        install_agents(
            mm_bin=tmp_path / "mm",
            agents_dir=agents_dir,
            logs_dir=tmp_path / "logs",
            uid=501,
            runner=_ok,
            darwin=False,
        )
        monkeypatch.setattr("macmanager.agents.platform.system", lambda: "Darwin")
        monkeypatch.setattr("macmanager.agents.launch_agents_dir", lambda: agents_dir)
        monkeypatch.setattr("macmanager.agents.os.getuid", lambda: 501)
        monkeypatch.setattr("macmanager.agents._default_launchctl", _ok)
        buf = StringIO()
        monkeypatch.setattr(
            "macmanager.agents.console",
            Console(file=buf, force_terminal=True, width=80),
        )
        assert cmd_uninstall() == 0
        assert "Removed launchd agents" in buf.getvalue()
        assert list(agents_dir.glob("*.plist")) == []


class TestParser:
    def test_setup_and_uninstall_are_advertised(self) -> None:
        help_text = build_parser().format_help()
        assert "setup" in help_text
        assert "uninstall" in help_text
