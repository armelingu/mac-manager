"""Tests for the pure pieces of `macmanager.security`.

Actual `check_*` functions shell out to macOS-only binaries and aren't
unit-tested here. We do lock in the scoring contract (`STATUS_SCORE`),
the `Check` dataclass fields, and the `CHECKS` registry — those are
cheap to validate and break loudly when someone refactors the module.
"""

from __future__ import annotations

from dataclasses import fields

import pytest

from macmanager.security import CHECKS, FAIL, INFO, OK, STATUS_SCORE, WARN, Check


class TestStatusConstants:
    @pytest.mark.parametrize(
        ("constant", "expected"),
        [
            (OK, "OK"),
            (WARN, "WARN"),
            (FAIL, "FAIL"),
            (INFO, "INFO"),
        ],
    )
    def test_string_values_are_stable(self, constant: str, expected: str) -> None:
        assert constant == expected

    def test_constants_are_distinct(self) -> None:
        assert len({OK, WARN, FAIL, INFO}) == 4


class TestStatusScore:
    def test_has_entries_for_all_statuses(self) -> None:
        assert set(STATUS_SCORE.keys()) == {OK, WARN, FAIL, INFO}

    @pytest.mark.parametrize(
        ("status", "expected_score"),
        [
            (OK, 1.0),
            (INFO, 1.0),  # INFO rows don't penalize the score
            (WARN, 0.4),
            (FAIL, 0.0),
        ],
    )
    def test_score_values(self, status: str, expected_score: float) -> None:
        assert STATUS_SCORE[status] == expected_score

    def test_all_scores_are_in_zero_to_one(self) -> None:
        for score in STATUS_SCORE.values():
            assert 0.0 <= score <= 1.0


class TestCheckDataclass:
    def test_has_expected_fields(self) -> None:
        names = {f.name for f in fields(Check)}
        assert names == {"name", "status", "detail", "weight", "tip"}

    def test_default_weight_is_one(self) -> None:
        c = Check(name="X", status=OK, detail="ok")
        assert c.weight == 1

    def test_default_tip_is_empty_string(self) -> None:
        c = Check(name="X", status=OK, detail="ok")
        assert c.tip == ""


class TestChecksRegistry:
    def test_is_non_empty(self) -> None:
        # If someone nukes the list, the audit panel renders empty and
        # the score becomes division-by-zero. Catch that here.
        assert len(CHECKS) > 0

    def test_entries_are_callable(self) -> None:
        for check in CHECKS:
            assert callable(check), f"{check!r} in CHECKS is not callable"

    def test_expected_checks_are_present(self) -> None:
        """Locks in the audit contract. If a check is removed it should be
        a deliberate decision (and this test updated alongside)."""
        names = {fn.__name__ for fn in CHECKS}
        expected = {
            "check_filevault",
            "check_firewall",
            "check_sip",
            "check_gatekeeper",
        }
        missing = expected - names
        assert not missing, f"expected checks missing from CHECKS: {missing}"
