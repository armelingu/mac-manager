"""Tests for the pure surface of `macmanager.dev`:

- `_t(name, cmd=...)` factory (defaults propagation)
- `GROUPS` registry (structure, uniqueness, non-empty groups)
- `_JDK_MISSING_HINTS` contract (all lowercase substrings)

The actual `_probe` function shells out — not covered here.
"""

from __future__ import annotations

from dataclasses import fields

import pytest

from macmanager.dev import _JDK_MISSING_HINTS, GROUPS, Tool, _t


class TestToolFactory:
    def test_defaults_cmd_to_name_when_missing(self) -> None:
        tool = _t("ruff")
        assert tool.name == "ruff"
        assert tool.cmd == "ruff"
        assert tool.version_args == ("--version",)

    def test_explicit_cmd_overrides_name(self) -> None:
        tool = _t("Node.js", "node")
        assert tool.name == "Node.js"
        assert tool.cmd == "node"

    def test_propagates_keyword_args(self) -> None:
        tool = _t(
            "Docker",
            "docker",
            version_args=("--version",),
            version_regex=r"Docker version (\S+)",
        )
        assert tool.version_regex == r"Docker version (\S+)"

    def test_returned_instance_is_a_Tool(self) -> None:
        assert isinstance(_t("go"), Tool)


class TestToolDataclass:
    def test_has_expected_fields(self) -> None:
        names = {f.name for f in fields(Tool)}
        assert names == {
            "name",
            "cmd",
            "version_args",
            "version_regex",
            "found",
            "version",
            "path",
        }

    def test_default_found_is_false(self) -> None:
        # `_probe` flips this to True only after `shutil.which` succeeds.
        assert _t("anything").found is False

    def test_default_version_is_none(self) -> None:
        assert _t("anything").version is None
        assert _t("anything").path is None


class TestGroups:
    def test_groups_is_non_empty(self) -> None:
        assert len(GROUPS) > 0

    def test_every_group_has_at_least_one_tool(self) -> None:
        for group_name, tools in GROUPS.items():
            assert tools, f"group {group_name!r} is empty"

    def test_every_entry_is_a_Tool(self) -> None:
        for group_name, tools in GROUPS.items():
            for tool in tools:
                assert isinstance(tool, Tool), f"{group_name!r} contains a non-Tool entry: {tool!r}"

    def test_tool_names_are_unique_within_a_group(self) -> None:
        for group_name, tools in GROUPS.items():
            names = [t.name for t in tools]
            dupes = {n for n in names if names.count(n) > 1}
            assert not dupes, f"duplicate tool names in {group_name!r}: {dupes}"

    def test_expected_core_groups_are_present(self) -> None:
        # Locks in the product contract: removing "Languages" silently
        # would be a noticeable UX regression.
        assert "Languages" in GROUPS

    def test_each_tool_cmd_is_non_empty(self) -> None:
        for tools in GROUPS.values():
            for tool in tools:
                assert tool.cmd, f"{tool.name!r} has an empty `cmd`"


class TestJdkMissingHints:
    def test_non_empty(self) -> None:
        assert _JDK_MISSING_HINTS

    def test_entries_are_lowercase(self) -> None:
        # The probe lowercases the command output before matching, so
        # the hints must be lowercase too or they'll never fire.
        for hint in _JDK_MISSING_HINTS:
            assert hint == hint.lower(), f"hint is not lowercase: {hint!r}"

    @pytest.mark.parametrize(
        "stub_output",
        [
            "No Java runtime present, requesting install.",
            "The operation couldn't be completed. Unable to locate a Java Runtime.",
            "no jvm installation found",
        ],
    )
    def test_realistic_stub_outputs_match(self, stub_output: str) -> None:
        lower = stub_output.lower()
        assert any(h in lower for h in _JDK_MISSING_HINTS), (
            f"no hint matched stub output: {stub_output!r}"
        )
