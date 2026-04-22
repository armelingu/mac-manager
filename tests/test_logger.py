"""Contract tests for `macmanager.logger`.

We don't exercise the CSV writer directly (it touches the filesystem via
a module-level global path and pulls in a real battery reading). We DO
pin the schema: once the CSV has columns in a given order, changing that
order silently breaks every deployed history file.
"""

from __future__ import annotations

from pathlib import Path

from macmanager.logger import ALERT_STATE, BATTERY_CSV, BATTERY_FIELDS, LOGS_DIR


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
