"""Contract tests for `macmanager.logger`.

We don't exercise the CSV writer directly (it touches the filesystem via
a module-level global path and pulls in a real battery reading). We DO
pin the schema: once the CSV has columns in a given order, changing that
order silently breaks every deployed history file.
"""

from __future__ import annotations

from pathlib import Path

from macmanager.logger import (
    ALERT_STATE,
    BATTERY_CSV,
    BATTERY_FIELDS,
    LOGS_DIR,
    default_logs_dir,
    migrate_legacy,
    resolve_logs_dir,
)


class TestBatteryFields:
    def test_is_non_empty_list(self) -> None:
        assert isinstance(BATTERY_FIELDS, list)
        assert len(BATTERY_FIELDS) > 0

    def test_has_unique_entries(self) -> None:
        assert len(BATTERY_FIELDS) == len(set(BATTERY_FIELDS))

    def test_timestamp_is_first_column(self) -> None:
        # History readers scan column 0 first when bisecting by date.
        assert BATTERY_FIELDS[0] == "timestamp"

    def test_column_order_is_pinned(self) -> None:
        """Exact order is the CSV contract. If a column is appended at the
        end (without reordering), downstream readers still work. Anything
        else is a breaking change — update this test and the CHANGELOG
        together."""
        assert BATTERY_FIELDS == [
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


class TestPaths:
    def test_logs_dir_is_absolute_path(self) -> None:
        assert isinstance(LOGS_DIR, Path)
        assert LOGS_DIR.is_absolute()

    def test_battery_csv_lives_under_logs_dir(self) -> None:
        assert BATTERY_CSV.parent == LOGS_DIR
        assert BATTERY_CSV.name == "battery.csv"

    def test_alert_state_lives_under_logs_dir(self) -> None:
        assert ALERT_STATE.parent == LOGS_DIR
        # Dotfile so it doesn't clutter `ls`.
        assert ALERT_STATE.name.startswith(".")

    def test_logs_dir_is_not_inside_the_package(self) -> None:
        # pipx/Homebrew upgrade apagava site-packages/logs/. O diretório
        # de dados tem que viver fora da árvore do pacote.
        package_root = Path(__file__).resolve().parents[1]
        # tests/ está na raiz do repo; o logger antigo usava <repo>/logs.
        assert package_root / "logs" != LOGS_DIR


class TestResolveLogsDir:
    def test_env_override_wins(self, tmp_path: Path) -> None:
        resolved = resolve_logs_dir(env={"MACMANAGER_LOGS_DIR": str(tmp_path)})
        assert resolved == tmp_path.resolve()

    def test_empty_override_falls_back_to_default(self, tmp_path: Path) -> None:
        resolved = resolve_logs_dir(
            env={"MACMANAGER_LOGS_DIR": "  "},
            home=tmp_path,
            system="Darwin",
        )
        assert resolved == tmp_path / "Library" / "Application Support" / "mac-manager"

    def test_darwin_uses_application_support(self, tmp_path: Path) -> None:
        assert default_logs_dir(home=tmp_path, system="Darwin") == (
            tmp_path / "Library" / "Application Support" / "mac-manager"
        )

    def test_linux_uses_xdg_data_home(self, tmp_path: Path) -> None:
        assert default_logs_dir(home=tmp_path, system="Linux") == (
            tmp_path / ".local" / "share" / "mac-manager"
        )


class TestMigrateLegacy:
    def test_copies_missing_files(self, tmp_path: Path) -> None:
        legacy = tmp_path / "legacy"
        dest = tmp_path / "dest"
        legacy.mkdir()
        (legacy / "battery.csv").write_text("ts,percent\n", encoding="utf-8")
        (legacy / ".alert_state").write_text("{}", encoding="utf-8")

        copied = migrate_legacy(legacy, dest)
        assert set(copied) == {"battery.csv", ".alert_state"}
        assert (dest / "battery.csv").read_text(encoding="utf-8") == "ts,percent\n"
        assert (dest / ".alert_state").read_text(encoding="utf-8") == "{}"

    def test_does_not_overwrite_existing_dest(self, tmp_path: Path) -> None:
        legacy = tmp_path / "legacy"
        dest = tmp_path / "dest"
        legacy.mkdir()
        dest.mkdir()
        (legacy / "battery.csv").write_text("old\n", encoding="utf-8")
        (dest / "battery.csv").write_text("new\n", encoding="utf-8")

        assert migrate_legacy(legacy, dest) == []
        assert (dest / "battery.csv").read_text(encoding="utf-8") == "new\n"

    def test_same_dir_is_a_noop(self, tmp_path: Path) -> None:
        (tmp_path / "battery.csv").write_text("x\n", encoding="utf-8")
        assert migrate_legacy(tmp_path, tmp_path) == []
