"""Smoke tests.

These tests do not verify business logic — they just make sure that every
public module imports cleanly on every supported Python version and that
the package-level metadata is consistent. This is the safety net that
keeps CI green until a proper unit-test suite is written.

Platform note: several modules shell out to macOS-only binaries
(`ioreg`, `pmset`, `system_profiler`, etc.) at *call* time, not at
import time — so importing them on Linux runners is safe.
"""

from __future__ import annotations

import importlib
import re

import pytest

import macmanager

PUBLIC_MODULES = [
    "macmanager",
    "macmanager.alerts",
    "macmanager.battery",
    "macmanager.cache",
    "macmanager.cli",
    "macmanager.dev",
    "macmanager.disk",
    "macmanager.doctor",
    "macmanager.logger",
    "macmanager.network",
    "macmanager.notify",
    "macmanager.security",
    "macmanager.system",
    "macmanager.ui",
    "macmanager.watch",
]

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+.].*)?$")


def test_package_exposes_version() -> None:
    assert hasattr(macmanager, "__version__")
    assert isinstance(macmanager.__version__, str)
    assert macmanager.__version__, "__version__ must not be empty"
    assert SEMVER.match(macmanager.__version__), (
        f"__version__ {macmanager.__version__!r} does not look like SemVer"
    )


@pytest.mark.parametrize("module_name", PUBLIC_MODULES)
def test_module_imports_cleanly(module_name: str) -> None:
    importlib.import_module(module_name)


def test_cli_parser_builds_and_advertises_all_commands() -> None:
    from macmanager.cli import build_parser

    parser = build_parser()
    assert parser.prog == "mm"

    help_text = parser.format_help()
    for command in (
        "battery",
        "health",
        "disk",
        "clean",
        "net",
        "doctor",
        "log",
        "history",
        "watch",
        "alerts",
        "status",
        "security",
        "dev",
    ):
        assert command in help_text, f"CLI help is missing the `{command}` subcommand"


def test_cli_version_flag_matches_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    from macmanager.cli import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--version"])
    assert exc.value.code == 0

    captured = capsys.readouterr().out
    assert macmanager.__version__ in captured
